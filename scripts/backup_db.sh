#!/usr/bin/env bash
# ============================================================================
# SCRIPT DE RESPALDO AUTOMÁTICO POSTGRESQL (LINUX / DOCKER / CRON)
# Hospital Escandón - Cumplimiento NOM-024 / NOM-004
# ============================================================================

set -euo pipefail

DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
DB_NAME="${PGDATABASE:-hospital_escandon_db}"
DB_USER="${PGUSER:-postgres}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/../backups"
mkdir -p "${BACKUP_DIR}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/hes_backup_${TIMESTAMP}.sql.gz"

echo "======================================================="
echo "[HES BACKUP ENGINE] Iniciando respaldo..."
echo "Fecha:    $(date)"
echo "Base DB:  ${DB_NAME} en ${DB_HOST}:${DB_PORT}"
echo "Archivo:  ${BACKUP_FILE}"
echo "======================================================="

pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -F p | gzip > "${BACKUP_FILE}"

echo "[ÉXITO] Respaldo generado correctamente ($(du -h "${BACKUP_FILE}" | cut -f1))"

# Rotación de respaldos: conservar últimos 14 días
find "${BACKUP_DIR}" -name "hes_backup_*.sql.gz" -type f -mtime +14 -delete
echo "[ROTACIÓN] Archivos de más de 14 días eliminados."
