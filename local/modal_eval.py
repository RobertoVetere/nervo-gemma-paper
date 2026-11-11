"""Evaluación en Modal con el mismo entorno que el kernel de Kaggle (y que el examen, salvo la imagen Docker).

Igual que Kaggle: 4 GPU L4, vLLM 0.19.1 y las demás versiones del wheelhouse oficial, los pesos cuantizados
oficiales (google/gemma-4-*-it-qat-w4a16-ct de Hugging Face), el harness oficial (swegemma, adk_submission,
adk_eval_core) y el mismo kernel (scripts/kernel_template.py renderizado con render_kernel.py).
Lo lanza el workflow .github/workflows/modal.yml (desde esta sesión no hay salida gRPC a Modal).

  modal run local/modal_eval.py --kernel kernel/kernel.py --datos datos.tar --modelo gemma-4-31b-it-qat-w4a16-ct --out salida
"""
import io
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import modal

app = modal.App('nervo-eval')
modelos = modal.Volume.from_name('nervo-modelos', create_if_missing=True)
# El tar de datos (1,7 GB) se sube UNA vez al volumen con `modal volume put` (lo hace el workflow): mandarlo como
# argumento a cada contenedor llenaba la memoria del runner de GitHub (exit 143 con 5 contenedores).
datosvol = modal.Volume.from_name('nervo-datos', create_if_missing=True)

# Versiones exactas del wheelhouse oficial de la competición (gemma-4-developer-agent-wheelhouse).
WHEELHOUSE = [
    'transformers==5.13.1', 'compressed-tensors==0.15.0.1', 'flashinfer-python==0.6.6', 'flashinfer-cubin==0.6.6',
    'xgrammar==0.2.5.post1', 'google-adk==1.36.1', 'google-genai==2.11.0', 'tokenizers==0.22.2',
    'safetensors==0.8.0', 'mistral-common==1.11.7', 'llguidance==1.3.0', 'outlines-core==0.2.11',
    'lm-format-enforcer==0.11.3', 'gguf==0.19.0', 'msgspec==0.21.1', 'partial-json-parser==0.2.1.1.post7',
    'openai-harmony==0.0.8', 'cbor2==6.1.4', 'apache-tvm-ffi==0.1.13.post3', 'quack-kernels==0.6.4',
    'nvidia-cudnn-frontend==1.18.0', 'depyf==0.20.0', 'diskcache==5.6.3', 'interegular==0.3.3', 'loguru==0.7.3',
    'pybase64==1.5.0', 'setproctitle==1.3.7', 'ijson==3.5.1', 'pycountry==26.2.16', 'pydantic-extra-types==2.11.2',
    'prometheus-fastapi-instrumentator==8.1.0', 'anthropic==1.4.0', 'bitsandbytes==0.46.1', 'astor==0.8.1',
    'model-hosting-container-standards==0.1.16', 'opentelemetry-exporter-otlp==1.44.0',
    'opentelemetry-semantic-conventions-ai==0.5.1',
]
RAIZ = Path(__file__).resolve().parent.parent

imagen = (
    modal.Image.debian_slim(python_version='3.12')
    .apt_install('git', 'patch', 'pigz', 'protobuf-compiler', 'build-essential')
    .pip_install('vllm==0.19.1', 'huggingface_hub>=1.5,<2', 'pyyaml', 'rich', 'docker', 'pytest',
                 'litellm==1.99.4', 'pandas', 'accelerate')  # pandas y accelerate: dependencias de swegemma
    .run_commands('pip install --no-deps ' + ' '.join(WHEELHOUSE))
    .add_local_dir(str(RAIZ / 'modal_wheels'), '/harness_wheels', copy=True)
    .run_commands('pip install --no-deps /harness_wheels/*.whl')
    # --no-deps deja fuera las dependencias de google-adk/google-genai (google-auth, opentelemetry, ...): se instalan
    # aquí resolviendo, sin dejar que muevan las versiones fijadas del wheelhouse.
    .run_commands("pip install google-adk==1.36.1 google-genai==2.11.0 litellm==1.99.4 transformers==5.13.1 "
                  "'huggingface_hub>=1.5,<2' compressed-tensors==0.15.0.1 vllm==0.19.1")
    
)

REPOS_HF = {
    'gemma-4-e4b-it-qat-w4a16-ct': 'google/gemma-4-E4B-it-qat-w4a16-ct',
    'gemma-4-31b-it-qat-w4a16-ct': 'google/gemma-4-31B-it-qat-w4a16-ct',
}


@app.function(image=imagen, gpu='L4:4', cpu=8, memory=49152, timeout=170 * 60,
              volumes={'/modelos': modelos, '/datosvol': datosvol},
              secrets=[modal.Secret.from_dict({'HF_TOKEN': os.environ.get('HF_TOKEN', '')})])
def evaluar(kernel: bytes, datos: str, modelo: str, nombre: str = '') -> bytes:
    """datos: nombre del tar dentro del volumen nervo-datos."""
    t0 = time.time()
    destino = Path('/modelos') / modelo
    if not (destino / 'config.json').exists():
        from huggingface_hub import snapshot_download
        snapshot_download(REPOS_HF[modelo], local_dir=str(destino), token=os.environ.get('HF_TOKEN') or None)
        modelos.commit()
    print(f'[modal] modelo listo en {time.time() - t0:.0f}s', flush=True)
    Path('/data').mkdir(exist_ok=True)
    tarfile.open(f'/datosvol/{datos}').extractall('/data', filter='data')
    Path('/work').mkdir(exist_ok=True)
    Path('/work/kernel.py').write_bytes(kernel)
    env = dict(os.environ, NERVO_DATA='/data', NERVO_MODEL_DIR='/modelos', NERVO_SKIP_WHEELHOUSE='1',
               NERVO_WORKDIR='/work/out')
    subprocess.run(['nvidia-smi', '-L'], check=False)
    r = subprocess.run([sys.executable, '/work/kernel.py'], cwd='/work', env=env)
    seg = time.time() - t0
    print(f'[modal] kernel terminó con código {r.returncode} en {seg:.0f}s; coste GPU aprox. {seg / 3600 * 4 * 0.80:.2f} USD (4x L4)', flush=True)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        if Path('/work/out').exists():
            tf.add('/work/out', arcname='salida')
    if nombre:  # modo desacoplado: el resultado queda en el volumen y lo recoge el workflow "Recoger resultados de Modal"
        os.makedirs('/datosvol/resultados', exist_ok=True)
        Path(f'/datosvol/resultados/{nombre}.tar.gz').write_bytes(buf.getvalue())
        datosvol.commit()
        print(f'[modal] resultado guardado en el volumen nervo-datos: resultados/{nombre}.tar.gz', flush=True)
    return buf.getvalue()


@app.function(image=imagen, timeout=900)
def comprobar() -> str:
    """Sin GPU (céntimos): importa todo lo que el kernel necesita. Si falla, no se gasta GPU."""
    out = []
    for mod in ('torch', 'vllm', 'transformers', 'huggingface_hub', 'swegemma', 'adk_submission', 'adk_eval_core',
                'google.adk', 'litellm', 'compressed_tensors'):
        m = __import__(mod, fromlist=['_'])
        out.append(f'{mod} {getattr(m, "__version__", "?")}')
    from vllm.engine.arg_utils import EngineArgs  # noqa: F401  (aquí falló la primera vez: huggingface_hub 2.x)
    from adk_submission import VllmServer  # noqa: F401
    from swegemma.evaluate import Evaluator, verify_task  # noqa: F401
    # todo lo que importa el kernel (scripts/kernel_template.py)
    from adk_submission import VllmConfig, discover_adapters, validate_directory  # noqa: F401
    from adk_submission.registry import ModelRegistry  # noqa: F401
    from adk_submission.resolvers.generation import install_litellm_reasoning_patch  # noqa: F401
    from adk_submission.discovery import discover_declared_models  # noqa: F401
    from google.adk.models.lite_llm import LiteLlm  # noqa: F401
    from google.adk.agents.context_cache_config import ContextCacheConfig  # noqa: F401
    from google.adk.apps._configs import EventsCompactionConfig  # noqa: F401
    from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS, build_submission_limits, EvalConfig  # noqa: F401
    from swegemma.deduplication import resolve_task_snapshot_paths  # noqa: F401
    from swegemma.models import load_tasks  # noqa: F401
    from swegemma.sandbox import subprocess as sbx  # noqa: F401
    import yaml, litellm  # noqa: F401
    import subprocess as sp
    chk = sp.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True).stdout
    faltan = [l for l in chk.splitlines() if 'which is not installed' in l]
    out.append('pip check: ' + (f'{len(faltan)} dependencias que faltan:\n' + '\n'.join(faltan) if faltan else 'nada falta'))
    return '\n'.join(out)


@app.local_entrypoint()
def solo_comprobar():
    print(comprobar.remote())


@app.local_entrypoint()
def main(kernel: str, datos: str, modelo: str, out: str = 'salida', esperar: int = 1, nombre: str = ''):
    """datos: nombre del tar ya subido al volumen nervo-datos. kernel: uno o varios kernels separados por comas (una variante o repetición cada uno). Cada uno corre en su
    propio contenedor de 4 L4, todos a la vez; los resultados van a <out>/<i>/."""
    kernels = [k for k in kernel.split(',') if k]
    if not esperar:
        # `modal run --detach`: el runner de GitHub lanza y se va (no gasta minutos esperando GPU). Con --detach Modal
        # solo mantiene viva la ÚLTIMA función lanzada, así que aquí va un único contenedor.
        assert len(kernels) == 1, 'en modo desacoplado, un solo contenedor por ejecución'
        ll = evaluar.spawn(Path(kernels[0]).read_bytes(), datos, modelo, nombre)
        print(f'[modal] lanzado sin esperar: {ll.object_id}; resultado en nervo-datos:resultados/{nombre}.tar.gz', flush=True)
        return
    llamadas = [evaluar.spawn(Path(k).read_bytes(), datos, modelo) for k in kernels]
    for i, (k, ll) in enumerate(zip(kernels, llamadas)):
        try:
            res = ll.get()
        except Exception as e:  # noqa: BLE001  (un contenedor que falla no tira los demás)
            print(f'[modal] {k} falló: {e}', flush=True); continue
        dest = Path(out) / str(i); dest.mkdir(parents=True, exist_ok=True)
        tarfile.open(fileobj=io.BytesIO(res)).extractall(dest, filter='data')
        print('resultados de', k, 'en', dest, flush=True)
