"""Evaluation on Modal with the same environment as the Kaggle kernel (and the competition, except the Docker image).

As on Kaggle: 4 L4 GPUs, vLLM 0.19.1 and the other versions of the official wheelhouse, the official quantized weights
(google/gemma-4-*-it-qat-w4a16-ct from Hugging Face), the official harness (swegemma, adk_submission, adk_eval_core)
and the same kernel (scripts/kernel_template.py rendered with scripts/render_kernel.py).
Launched by the workflow .github/workflows/modal.yml. CLI argument names follow the function parameters
(datos = data tar in the volume, modelo = model, esperar = wait, nombre = result name).

  modal run local/modal_eval.py --kernel kernel/kernel.py --datos data.tar --modelo gemma-4-31b-it-qat-w4a16-ct --out output
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
# The data tar (1.7 GB) is uploaded ONCE to the volume with `modal volume put` (the workflow does it): passing it as an
# argument to each container filled the GitHub runner's memory (exit 143 with 5 containers).
datosvol = modal.Volume.from_name('nervo-datos', create_if_missing=True)

# Exact versions from the competition's official wheelhouse (gemma-4-developer-agent-wheelhouse).
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
                 'litellm==1.99.4', 'pandas', 'accelerate')  # pandas and accelerate: swegemma dependencies
    .run_commands('pip install --no-deps ' + ' '.join(WHEELHOUSE))
    .add_local_dir(str(RAIZ / 'modal_wheels'), '/harness_wheels', copy=True)
    .run_commands('pip install --no-deps /harness_wheels/*.whl')
    # --no-deps leaves out the dependencies of google-adk/google-genai (google-auth, opentelemetry, ...): they are
    # installed here with resolution, without letting them move the pinned wheelhouse versions.
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
    """datos: name of the data tar inside the nervo-datos volume."""
    t0 = time.time()
    destino = Path('/modelos') / modelo
    if not (destino / 'config.json').exists():
        from huggingface_hub import snapshot_download
        snapshot_download(REPOS_HF[modelo], local_dir=str(destino), token=os.environ.get('HF_TOKEN') or None)
        modelos.commit()
    print(f'[modal] model ready in {time.time() - t0:.0f}s', flush=True)
    Path('/data').mkdir(exist_ok=True)
    tarfile.open(f'/datosvol/{datos}').extractall('/data', filter='data')
    Path('/work').mkdir(exist_ok=True)
    Path('/work/kernel.py').write_bytes(kernel)
    env = dict(os.environ, NERVO_DATA='/data', NERVO_MODEL_DIR='/modelos', NERVO_SKIP_WHEELHOUSE='1',
               NERVO_WORKDIR='/work/out')
    subprocess.run(['nvidia-smi', '-L'], check=False)
    r = subprocess.run([sys.executable, '/work/kernel.py'], cwd='/work', env=env)
    seg = time.time() - t0
    print(f'[modal] kernel finished with code {r.returncode} in {seg:.0f}s; approx. GPU cost {seg / 3600 * 4 * 0.80:.2f} USD (4x L4)', flush=True)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        if Path('/work/out').exists():
            tf.add('/work/out', arcname='output')
    if nombre:  # detached mode: the result stays in the volume and the workflow collect_modal.yml picks it up
        os.makedirs('/datosvol/results', exist_ok=True)
        Path(f'/datosvol/results/{nombre}.tar.gz').write_bytes(buf.getvalue())
        datosvol.commit()
        print(f'[modal] result saved in the nervo-datos volume: results/{nombre}.tar.gz', flush=True)
    return buf.getvalue()


@app.function(image=imagen, timeout=900)
def comprobar() -> str:
    """No GPU (cents): import everything the kernel needs. If it fails, no GPU time is spent."""
    out = []
    for mod in ('torch', 'vllm', 'transformers', 'huggingface_hub', 'swegemma', 'adk_submission', 'adk_eval_core',
                'google.adk', 'litellm', 'compressed_tensors'):
        m = __import__(mod, fromlist=['_'])
        out.append(f'{mod} {getattr(m, "__version__", "?")}')
    from vllm.engine.arg_utils import EngineArgs  # noqa: F401  (this failed the first time: huggingface_hub 2.x)
    from adk_submission import VllmServer  # noqa: F401
    from swegemma.evaluate import Evaluator, verify_task  # noqa: F401
    # everything the kernel imports (scripts/kernel_template.py)
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
    out.append('pip check: ' + (f'{len(faltan)} missing dependencies:\n' + '\n'.join(faltan) if faltan else 'nothing missing'))
    return '\n'.join(out)


@app.local_entrypoint()
def solo_comprobar():
    print(comprobar.remote())


@app.local_entrypoint()
def main(kernel: str, datos: str, modelo: str, out: str = 'output', esperar: int = 1, nombre: str = ''):
    """datos: name of the tar already in the nervo-datos volume. kernel: one or more comma-separated kernels (one variant or
    replica each). Each runs in its own 4xL4 container, all at once; results go to <out>/<i>/."""
    kernels = [k for k in kernel.split(',') if k]
    if not esperar:
        # `modal run --detach`: the GitHub runner launches and leaves (no minutes spent waiting for a GPU). With --detach
        # Modal keeps only the LAST launched function alive, so a single container goes here.
        assert len(kernels) == 1, 'in detached mode, one container per run'
        ll = evaluar.spawn(Path(kernels[0]).read_bytes(), datos, modelo, nombre)
        print(f'[modal] launched without waiting: {ll.object_id}; result in nervo-datos:results/{nombre}.tar.gz', flush=True)
        return
    llamadas = [evaluar.spawn(Path(k).read_bytes(), datos, modelo) for k in kernels]
    for i, (k, ll) in enumerate(zip(kernels, llamadas)):
        try:
            res = ll.get()
        except Exception as e:  # noqa: BLE001  (a failing container does not stop the others)
            print(f'[modal] {k} failed: {e}', flush=True); continue
        dest = Path(out) / str(i); dest.mkdir(parents=True, exist_ok=True)
        tarfile.open(fileobj=io.BytesIO(res)).extractall(dest, filter='data')
        print('results of', k, 'in', dest, flush=True)
