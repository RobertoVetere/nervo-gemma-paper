"""Servidor vLLM en Modal con el modelo CUANTIZADO oficial, como API compatible con OpenAI.

Mismo vLLM (0.19.1), mismos parsers (gemma4), mismo contexto (32768) y mismos pesos (qat-w4a16-ct) que el examen.
Sirve para llamar al modelo de Kaggle desde fuera: sondas one shot y el harness local (local/correr_local.py vía
local/shim_vllm.py --backend modal). Se apaga solo tras 5 min sin peticiones (no factura en reposo).
Clave de acceso: sha256(MODAL_TOKEN_SECRET + ':vllm')[:40] (la calculan el workflow y la sesión, sin publicarla).

  modal deploy local/modal_vllm.py      (lo hace el workflow "Servidor vLLM en Modal")
URL: https://<workspace>--nervo-vllm-<modelo>.modal.run/v1
"""
import hashlib
import os
import subprocess

import modal

MODELO = os.environ.get('NERVO_VLLM_MODELO', 'gemma-4-e4b-it-qat-w4a16-ct')
GPUS = int(os.environ.get('NERVO_VLLM_GPUS', '1'))
REPOS_HF = {
    'gemma-4-e4b-it-qat-w4a16-ct': 'google/gemma-4-E4B-it-qat-w4a16-ct',
    'gemma-4-31b-it-qat-w4a16-ct': 'google/gemma-4-31B-it-qat-w4a16-ct',
}
CLAVE = hashlib.sha256((os.environ.get('MODAL_TOKEN_SECRET', '') + ':vllm').encode()).hexdigest()[:40]
CORTO = 'e4b' if 'e4b' in MODELO else '31b'

app = modal.App(f'nervo-vllm-{CORTO}')
modelos = modal.Volume.from_name('nervo-modelos', create_if_missing=True)
imagen = (
    modal.Image.debian_slim(python_version='3.12')
    .pip_install('vllm==0.19.1', 'huggingface_hub>=1.5,<2')
    .run_commands('pip install --no-deps transformers==5.13.1 compressed-tensors==0.15.0.1 flashinfer-python==0.6.6 '
                  'flashinfer-cubin==0.6.6 xgrammar==0.2.5.post1 tokenizers==0.22.2 safetensors==0.8.0')
    .env({'NERVO_VLLM_MODELO': MODELO, 'NERVO_VLLM_GPUS': str(GPUS),
          'NERVO_VLLM_CLAVE': CLAVE})
)


# Si Modal no tiene L4 libre, usa A10 (24 GB, misma clase de GPU; ~1,10 $/h): mismo modelo y mismo vLLM.
@app.function(image=imagen, gpu=[f'L4:{GPUS}', f'A10:{GPUS}'], cpu=8, memory=32768, volumes={'/modelos': modelos},
              scaledown_window=300, timeout=3600, max_containers=1)
@modal.concurrent(max_inputs=64)
@modal.web_server(port=8000, startup_timeout=1200)
def servir():
    modelo = os.environ['NERVO_VLLM_MODELO']
    destino = f'/modelos/{modelo}'
    if not os.path.exists(f'{destino}/config.json'):
        from huggingface_hub import snapshot_download
        snapshot_download(REPOS_HF[modelo], local_dir=destino)
        modelos.commit()
    subprocess.Popen([
        'vllm', 'serve', destino, '--served-model-name', modelo, '--host', '0.0.0.0', '--port', '8000',
        '--tool-call-parser', 'gemma4', '--reasoning-parser', 'gemma4', '--enable-auto-tool-choice',
        '--max-model-len', '32768', '--gpu-memory-utilization', '0.90', '--dtype', 'bfloat16',
        '--tensor-parallel-size', os.environ['NERVO_VLLM_GPUS'], '--api-key', os.environ['NERVO_VLLM_CLAVE'],
    ])


@app.function(image=imagen, timeout=900)
def comprobar() -> str:
    """Sin GPU: importa lo que falló la primera vez (transformers exige huggingface_hub<2). La CLI de vLLM no
    arranca sin GPU ("Failed to infer device type"), así que se importa su módulo de argumentos."""
    import transformers, huggingface_hub, vllm
    from vllm.engine.arg_utils import EngineArgs  # noqa: F401
    return f'vllm {vllm.__version__} | transformers {transformers.__version__} | huggingface_hub {huggingface_hub.__version__}'


@app.local_entrypoint()
def solo_comprobar():
    print(comprobar.remote())
