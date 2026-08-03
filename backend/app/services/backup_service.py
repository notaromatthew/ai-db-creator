from pathlib import Path
from datetime import datetime
import shutil
import json
from app.utils.logger import log

BACKUPS_DIR = "backups"

class BackupService:
    def create_backup(self, db_path: str, project_id: str, label: str = "") -> dict:
        db_file = Path(db_path)
        if not db_file.exists():
            log.warning(f"Cannot backup: {db_path} not found")
            return {"error": "Database not found"}

        backup_dir = Path(db_path).parent / BACKUPS_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_label = "".join(c if c.isalnum() or c in " _-" else "_" for c in label)[:40]
        backup_name = f"{ts}_{safe_label}.db" if safe_label else f"{ts}.db"
        backup_path = backup_dir / backup_name

        shutil.copy2(str(db_file), str(backup_path))

        meta = {
            "timestamp": datetime.now().isoformat(),
            "label": label,
            "project_id": project_id,
            "file": backup_name,
            "size": backup_path.stat().st_size,
        }
        meta_path = backup_path.with_suffix(".json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        log.info(f"Backup created: {backup_path}")
        return meta

    def list_backups(self, project_id: str, db_path: str) -> list[dict]:
        backup_dir = Path(db_path).parent / BACKUPS_DIR
        if not backup_dir.exists():
            return []

        backups = []
        for f in sorted(backup_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.suffix == ".db":
                meta_path = f.with_suffix(".json")
                if meta_path.exists():
                    with open(meta_path) as mf:
                        meta = json.load(mf)
                else:
                    meta = {
                        "timestamp": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                        "label": "",
                        "file": f.name,
                        "size": f.stat().st_size,
                    }
                backups.append(meta)
        return backups

    def restore_backup(self, db_path: str, backup_name: str) -> dict:
        db_file = Path(db_path)
        backup_dir = db_file.parent / BACKUPS_DIR
        backup_path = backup_dir / backup_name

        if not backup_path.exists():
            return {"error": f"Backup not found: {backup_name}"}

        if db_file.exists():
            undo_name = f"undo_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            undo_path = backup_dir / undo_name
            shutil.copy2(str(db_file), str(undo_path))
            log.info(f"Pre-restore snapshot saved: {undo_path}")

        shutil.copy2(str(backup_path), str(db_file))
        log.info(f"Restored from backup: {backup_path}")
        return {"status": "restored", "backup": backup_name}

    def auto_backup(self, db_path: str, project_id: str, operation: str):
        """Create an automatic backup before a destructive operation."""
        return self.create_backup(db_path, project_id, label=f"auto_{operation}")
