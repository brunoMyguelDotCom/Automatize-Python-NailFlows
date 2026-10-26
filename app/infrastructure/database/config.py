import os
from pathlib import Path

from dotenv import load_dotenv


def load_supabase_config():
    """Carrega a configuração do backend sem depender do diretório de execução."""
    load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[:-len("/rest/v1")]
    key = (
        os.getenv("SUPABASE_SECRET_KEY", "").strip()
        or os.getenv("SUPABASE_KEY", "").strip()
    )
    if bool(url) != bool(key):
        raise ValueError(
            "Configure SUPABASE_URL e SUPABASE_SECRET_KEY (ou SUPABASE_KEY) "
            "para usar o Supabase; deixe ambas vazias para usar memória."
        )
    return url, key
