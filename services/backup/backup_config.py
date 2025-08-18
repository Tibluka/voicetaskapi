import os
import sys

# Adiciona o diretório raiz do projeto ao path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.append(project_root)

# Importa sua configuração existente
try:
    from config import MONGO_URI

    print("✅ Configuração MongoDB importada com sucesso")
except ImportError:
    print("❌ Erro: não foi possível importar MONGO_URI do config.py")
    print("💡 Certifique-se de estar no diretório correto do projeto")
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv()


class BackupConfig:
    # Reutiliza suas configurações existentes
    MONGO_URI = MONGO_URI
    DATABASE_NAME = "VoiceTask"

    # Coleções do seu projeto
    COLLECTIONS = ["spending", "users", "password_resets", "profile_config"]

    # Configurações AWS
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET = os.getenv("S3_BACKUP_BUCKET")

    # Configurações locais
    BACKUP_DIR = "./backups"
    LOG_DIR = "./logs"

    # Configurações de retenção
    LOCAL_RETENTION_DAYS = 7
    S3_RETENTION_DAYS = 365

    # Horários de backup
    BACKUP_TIMES = ["02:00", "14:00"]


def validate_config():
    """Valida se todas as configurações estão presentes"""
    config = BackupConfig()

    print("🔍 Validando configurações do VoiceTask Backup...")
    print(f"✅ MongoDB URI: {'✓ OK' if config.MONGO_URI else '❌ FALTANDO'}")
    print(f"✅ Database: {config.DATABASE_NAME}")
    print(f"✅ Coleções: {', '.join(config.COLLECTIONS)}")

    # Verificar AWS
    aws_checks = [
        ("AWS_ACCESS_KEY_ID", config.AWS_ACCESS_KEY_ID),
        ("AWS_SECRET_ACCESS_KEY", config.AWS_SECRET_ACCESS_KEY),
        ("S3_BUCKET", config.S3_BUCKET),
    ]

    missing = []
    for name, value in aws_checks:
        if value:
            print(f"✅ {name}: ✓ OK")
        else:
            print(f"❌ {name}: FALTANDO no .env")
            missing.append(name)

    if missing:
        print(f"\n⚠️ Adicione ao seu .env:")
        for var in missing:
            print(f"   {var}=sua_chave_aqui")
        return False

    print("\n🎉 Todas as configurações estão OK!")
    return True


if __name__ == "__main__":
    validate_config()
