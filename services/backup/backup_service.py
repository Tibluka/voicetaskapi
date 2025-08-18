# backup_system/backup.py
import os
import subprocess
import datetime
import json
import logging
import tarfile
import shutil
from pathlib import Path
from pymongo import MongoClient
import boto3
from botocore.exceptions import ClientError

from config import BackupConfig


class VoiceTaskBackup:
    def __init__(self):
        """Inicializa o sistema de backup"""
        self.config = BackupConfig()
        self.setup_logging()
        self.setup_directories()
        self.setup_mongo_connection()
        self.setup_s3_client()

        self.logger.info("🚀 Sistema de backup VoiceTask inicializado")

    def setup_logging(self):
        """Configura sistema de logs detalhado"""
        # Garante que o diretório de logs existe
        os.makedirs(self.config.LOG_DIR, exist_ok=True)

        # Configura formato dos logs
        log_format = "%(asctime)s - %(levelname)s - %(message)s"

        # Configura logging para arquivo e console
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(f"{self.config.LOG_DIR}/backup.log"),
                logging.StreamHandler(),  # Para ver no terminal também
            ],
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info("📝 Sistema de logging configurado")

    def setup_directories(self):
        """Cria diretórios necessários"""
        directories = [
            self.config.BACKUP_DIR,
            self.config.LOG_DIR,
            f"{self.config.BACKUP_DIR}/temp",
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            self.logger.info(f"📁 Diretório criado/verificado: {directory}")

    def setup_mongo_connection(self):
        """Testa e configura conexão com MongoDB"""
        try:
            self.mongo_client = MongoClient(self.config.MONGO_URI)
            self.db = self.mongo_client[self.config.DATABASE_NAME]

            # Testa a conexão
            self.mongo_client.admin.command("ping")
            self.logger.info("✅ Conexão com MongoDB estabelecida")

            # Verifica se as coleções existem
            existing_collections = self.db.list_collection_names()
            for collection in self.config.COLLECTIONS:
                if collection in existing_collections:
                    count = self.db[collection].count_documents({})
                    self.logger.info(f"📊 Coleção {collection}: {count} documentos")
                else:
                    self.logger.warning(f"⚠️ Coleção {collection} não encontrada")

        except Exception as e:
            self.logger.error(f"❌ Erro na conexão MongoDB: {e}")
            raise

    def setup_s3_client(self):
        """Configura cliente S3"""
        try:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=self.config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.config.AWS_SECRET_ACCESS_KEY,
                region_name=self.config.AWS_REGION,
            )

            # Testa a conexão listando buckets
            response = self.s3_client.list_buckets()
            self.logger.info("✅ Conexão com S3 estabelecida")

            # Verifica se o bucket existe
            bucket_exists = any(
                bucket["Name"] == self.config.S3_BUCKET
                for bucket in response["Buckets"]
            )

            if bucket_exists:
                self.logger.info(f"✅ Bucket {self.config.S3_BUCKET} encontrado")
            else:
                self.logger.error(f"❌ Bucket {self.config.S3_BUCKET} não encontrado")

        except Exception as e:
            self.logger.error(f"❌ Erro na conexão S3: {e}")
            raise

    def create_collection_backup(self, collection_name):
        """Cria backup de uma coleção específica"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = (
            f"{self.config.BACKUP_DIR}/temp/{collection_name}_{timestamp}.json"
        )

        try:
            # Exporta coleção para JSON
            self.logger.info(f"📤 Exportando coleção {collection_name}...")

            cmd = [
                "mongoexport",
                "--uri",
                self.config.MONGO_URI,
                "--db",
                self.config.DATABASE_NAME,
                "--collection",
                collection_name,
                "--out",
                backup_file,
                "--pretty",  # Formata o JSON de forma legível
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                # Verifica se arquivo foi criado e tem conteúdo
                if os.path.exists(backup_file) and os.path.getsize(backup_file) > 0:
                    self.logger.info(
                        f"✅ Coleção {collection_name} exportada com sucesso"
                    )
                    return backup_file
                else:
                    self.logger.error(f"❌ Arquivo de backup vazio: {collection_name}")
                    return None
            else:
                self.logger.error(
                    f"❌ Erro no mongoexport para {collection_name}: {result.stderr}"
                )
                return None

        except subprocess.TimeoutExpired:
            self.logger.error(f"❌ Timeout na exportação de {collection_name}")
            return None
        except Exception as e:
            self.logger.error(
                f"❌ Erro inesperado na exportação de {collection_name}: {e}"
            )
            return None

    def create_full_backup(self):
        """Cria backup completo de todas as coleções"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"{self.config.BACKUP_DIR}/backup_{timestamp}"

        self.logger.info("🔄 Iniciando backup completo...")

        try:
            # Cria diretório para este backup
            os.makedirs(backup_dir, exist_ok=True)

            backup_files = []
            backup_stats = {}

            # Faz backup de cada coleção
            for collection in self.config.COLLECTIONS:
                self.logger.info(f"🎯 Processando coleção: {collection}")

                # Conta documentos antes do backup
                doc_count = self.db[collection].count_documents({})
                backup_stats[collection] = doc_count

                if doc_count == 0:
                    self.logger.warning(f"⚠️ Coleção {collection} está vazia")
                    continue

                # Cria backup da coleção
                backup_file = self.create_collection_backup(collection)

                if backup_file:
                    # Move arquivo para diretório do backup
                    final_file = f"{backup_dir}/{collection}.json"
                    shutil.move(backup_file, final_file)
                    backup_files.append(final_file)

                    # Verifica tamanho do arquivo
                    file_size = os.path.getsize(final_file)
                    self.logger.info(
                        f"📦 {collection}: {doc_count} docs, {file_size} bytes"
                    )

            if not backup_files:
                self.logger.error("❌ Nenhum arquivo de backup foi criado")
                return None

            # Cria arquivo de metadados
            metadata = self.create_backup_metadata(backup_dir, backup_stats)

            # Comprime o backup
            compressed_file = self.compress_backup(backup_dir)

            if compressed_file:
                self.logger.info(f"✅ Backup completo criado: {compressed_file}")
                return compressed_file
            else:
                return None

        except Exception as e:
            self.logger.error(f"❌ Erro no backup completo: {e}")
            return None

    def create_backup_metadata(self, backup_dir, stats):
        """Cria arquivo com informações sobre o backup"""
        metadata = {
            "backup_date": datetime.datetime.now().isoformat(),
            "database": self.config.DATABASE_NAME,
            "collections": list(self.config.COLLECTIONS),
            "statistics": stats,
            "total_documents": sum(stats.values()),
            "backup_type": "full_export",
            "format": "JSON",
            "created_by": "VoiceTask Backup System v1.0",
        }

        metadata_file = f"{backup_dir}/backup_metadata.json"

        try:
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            self.logger.info(
                f"📋 Metadados criados: {metadata['total_documents']} documentos totais"
            )
            return metadata_file

        except Exception as e:
            self.logger.error(f"❌ Erro ao criar metadados: {e}")
            return None

    def compress_backup(self, backup_dir):
        """Comprime o diretório de backup"""
        compressed_file = f"{backup_dir}.tar.gz"

        try:
            self.logger.info("🗜️ Comprimindo backup...")

            with tarfile.open(compressed_file, "w:gz") as tar:
                tar.add(backup_dir, arcname=os.path.basename(backup_dir))

            # Verifica se a compressão foi bem-sucedida
            if os.path.exists(compressed_file):
                original_size = sum(
                    os.path.getsize(os.path.join(backup_dir, f))
                    for f in os.listdir(backup_dir)
                )
                compressed_size = os.path.getsize(compressed_file)

                compression_ratio = (1 - compressed_size / original_size) * 100

                self.logger.info(
                    f"✅ Compressão concluída: "
                    f"{original_size} → {compressed_size} bytes "
                    f"({compression_ratio:.1f}% redução)"
                )

                # Remove diretório original
                shutil.rmtree(backup_dir)

                return compressed_file
            else:
                self.logger.error("❌ Arquivo comprimido não foi criado")
                return None

        except Exception as e:
            self.logger.error(f"❌ Erro na compressão: {e}")
            return None
