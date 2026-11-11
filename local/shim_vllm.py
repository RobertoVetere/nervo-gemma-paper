"""Servidor local que se hace pasar por vLLM y reenvía a Google AI Studio (Gemma 4 31B).

El harness oficial habla con vLLM en formato OpenAI (/v1/chat/completions) y añade
campos propios de vLLM (extra_body.chat_template_kwargs, thinking_token_budget) que
AI Studio rechaza. Este shim:
  - quita esos campos y registra qué traían (para comprobar que el razonamiento iba activado),
  - cambia el nombre del modelo por el de AI Studio,
  - separa <thought>...</thought> del contenido y lo devuelve como reasoning_content,
    igual que el reasoning_parser gemma4 de vLLM,
  - guarda cada petición y respuesta en un .jsonl.

Uso: python local/shim_vllm.py --port 8000 --log /tmp/llamadas.jsonl
La clave se lee de ~/.aistudio_key (nunca del repo).

Con --backend deepinfra reenvía a DeepInfra (de pago, rápido, sirve E4B y 31B): el modelo se elige
según el nombre que pide el harness (e4b -> google/gemma-4-E4B-it, 31b -> google/gemma-4-31B-it),
se respeta chat_template_kwargs.enable_thinking y se corta al pasar --tope-usd de gasto acumulado.
Clave en ~/.deepinfra_key.
"""
import argparse
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
MODELO_GOOGLE = os.environ.get('SHIM_MODEL', 'gemma-4-31b-it')
CAMPOS_VLLM = ('chat_template_kwargs', 'thinking_token_budget', 'skip_special_tokens',
               'top_k', 'min_p', 'repetition_penalty', 'seed')
THOUGHT_RE = re.compile(r'<thought>(.*?)</thought>', re.S)

DEEPINFRA = 'https://api.deepinfra.com/v1/openai/chat/completions'
MODELOS_DEEPINFRA = {'e4b': 'google/gemma-4-E4B-it', '31b': 'google/gemma-4-31B-it'}
CAMPOS_FUERA_DEEPINFRA = ('thinking_token_budget', 'skip_special_tokens')

_lock = threading.Lock()
_contador = {'n': 0, 'usd': 0.0}


def adaptar_peticion_deepinfra(body):
    quitados = {k: body.pop(k) for k in CAMPOS_FUERA_DEEPINFRA if k in body}
    nombre = (body.get('model') or '').lower()
    clave = 'e4b' if 'e4b' in nombre else '31b' if '31b' in nombre else None
    if clave is None:
        raise ValueError(f'modelo no reconocido: {body.get("model")}')
    body['model'] = MODELOS_DEEPINFRA[clave]
    for m in body.get('messages', []):
        if isinstance(m, dict):
            m.pop('thinking_blocks', None)
    return body, quitados


def separar_pensamiento(content):
    """Devuelve (contenido_sin_thought, pensamiento) como hace el parser gemma4 de vLLM."""
    if not content:
        return content, None
    partes = THOUGHT_RE.findall(content)
    if not partes:
        return content, None
    limpio = THOUGHT_RE.sub('', content).strip()
    return (limpio or None), '\n'.join(p.strip() for p in partes)


def adaptar_peticion(body):
    """Convierte una petición del harness (formato vLLM) en una válida para AI Studio."""
    quitados = {k: body.pop(k) for k in CAMPOS_VLLM if k in body}
    body['model'] = MODELO_GOOGLE
    # thinking_budget 0 en el harness -> enable_thinking False. AI Studio no admite apagarlo para
    # Gemma, pero thinking_level "minimal" da 0 tokens de pensamiento (comprobado el 8-nov).
    if (quitados.get('chat_template_kwargs') or {}).get('enable_thinking') is False:
        body['extra_body'] = {'google': {'thinking_config': {'thinking_level': 'minimal'}}}
    # Los mensajes de asistente que llevan reasoning_content (include_thoughts) no son
    # campos válidos para Google: se quitan, como haría la plantilla de chat de Gemma.
    for m in body.get('messages', []):
        if isinstance(m, dict):
            m.pop('reasoning_content', None)
            m.pop('thinking_blocks', None)
    return body, quitados


def adaptar_respuesta(resp):
    for ch in resp.get('choices', []):
        msg = ch.get('message') or {}
        limpio, pensamiento = separar_pensamiento(msg.get('content'))
        msg['content'] = limpio
        if pensamiento:
            msg['reasoning_content'] = pensamiento
    return resp


class Handler(BaseHTTPRequestHandler):
    server_version = 'shim-vllm/0.1'

    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.rstrip('/').endswith('/models'):
            return self._json(200, {'object': 'list', 'data': [{'id': MODELO_GOOGLE, 'object': 'model'}]})
        self._json(200, {'ok': True})

    def do_POST(self):
        if not self.path.rstrip('/').endswith('/chat/completions'):
            return self._json(404, {'error': f'ruta no soportada: {self.path}'})
        n_bytes = int(self.headers.get('Content-Length', 0))
        original = json.loads(self.rfile.read(n_bytes) or b'{}')
        if original.get('stream'):
            # El harness no debería pedir streaming; si lo hace, que se vea enseguida.
            return self._json(400, {'error': 'shim: stream=True no soportado'})
        modelo_harness = original.get('model')
        deep = self.server.backend == 'deepinfra'
        modal_ = self.server.backend == 'modal'
        try:
            if modal_:  # vLLM real en Modal: la petición del harness pasa tal cual, como en Kaggle
                body, quitados = json.loads(json.dumps(original)), []
            else:
                body, quitados = (adaptar_peticion_deepinfra if deep else adaptar_peticion)(json.loads(json.dumps(original)))
        except ValueError as e:
            return self._json(400, {'error': str(e)})
        with _lock:
            if deep and _contador['usd'] >= self.server.tope_usd:
                return self._json(402, {'error': f'shim: tope de gasto alcanzado ({_contador["usd"]:.4f} USD)'})
            _contador['n'] += 1
            n = _contador['n']
        upstream = self.server.upstream if modal_ else (DEEPINFRA if deep else UPSTREAM)
        t0 = time.time()
        intentos, resp, error = 0, None, None
        while intentos < 6:
            intentos += 1
            req = urllib.request.Request(upstream, data=json.dumps(body).encode(), method='POST', headers={
                'Content-Type': 'application/json', 'Authorization': f'Bearer {self.server.key}'})
            try:
                with urllib.request.urlopen(req, timeout=600) as r:
                    resp = json.loads(r.read())
                error = None
                break
            except urllib.error.HTTPError as e:
                error = {'code': e.code, 'body': e.read().decode(errors='replace')[:2000]}
                if e.code in (429, 500, 502, 503, 504, 303):
                    time.sleep(min(60, 5 * 2 ** (intentos - 1)))
                    continue
                break
            except Exception as e:  # red
                error = {'code': None, 'body': f'{type(e).__name__}: {e}'}
                time.sleep(5)
        segundos = round(time.time() - t0, 1)
        coste = 0.0
        if resp is not None:
            if not deep and not modal_:
                resp = adaptar_respuesta(resp)
            coste = float((resp.get('usage') or {}).get('estimated_cost') or 0)
            resp['model'] = modelo_harness or resp.get('model')
        with _lock:
            _contador['usd'] += coste
            gastado = round(_contador['usd'], 6)
        registro = {'n': n, 't': time.strftime('%H:%M:%S'), 'segundos': segundos, 'intentos': intentos,
                    'coste_usd': coste, 'gastado_usd': gastado, 'backend': self.server.backend,
                    'modelo_harness': modelo_harness, 'campos_vllm_quitados': quitados,
                    'peticion': original, 'respuesta': resp, 'error': error}
        with _lock, open(self.server.log_path, 'a') as f:
            f.write(json.dumps(registro, ensure_ascii=False) + '\n')
        if resp is None:
            return self._json(error.get('code') or 502, {'error': error})
        self._json(200, resp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--log', default='/tmp/shim_llamadas.jsonl')
    ap.add_argument('--key-file', default='')
    ap.add_argument('--backend', choices=['aistudio', 'deepinfra', 'modal'], default='aistudio')
    ap.add_argument('--upstream', default='', help='solo modal: URL .../v1/chat/completions del servidor vLLM en Modal')
    ap.add_argument('--tope-usd', type=float, default=3.0, help='solo deepinfra: corta al pasar este gasto')
    a = ap.parse_args()
    srv = ThreadingHTTPServer(('127.0.0.1', a.port), Handler)
    kf = a.key_file or os.path.expanduser({'deepinfra': '~/.deepinfra_key', 'modal': '~/.modal_vllm_key'}.get(a.backend, '~/.aistudio_key'))
    srv.upstream = a.upstream
    srv.key = open(kf).read().strip()
    srv.log_path = a.log
    srv.backend = a.backend
    srv.tope_usd = a.tope_usd
    destino = a.upstream if a.backend == 'modal' else ('DeepInfra (e4b/31b según el harness)' if a.backend == 'deepinfra' else MODELO_GOOGLE)
    print(f'shim escuchando en 127.0.0.1:{a.port} -> {destino}; log {a.log}; tope {a.tope_usd} USD', flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
