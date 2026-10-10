"""SQLite migration acceptance and schema-drift rejection; not PostgreSQL certification."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

BACKEND = Path(__file__).resolve().parents[1]
class MigrationSafety(unittest.TestCase):
    def migrate(self,path):
        env={**os.environ,"DATABASE_URL":f"sqlite+aiosqlite:///{path}","NODE_ENV":"development","PCCC_DATA_DIR":str(path.parent/"files")}
        return subprocess.run([sys.executable,"-m","alembic","upgrade","head"],cwd=BACKEND,env=env,capture_output=True,text=True)
    def test_S27_fresh_migration_and_repeat_preserve_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbpath=Path(tmp)/"db.sqlite"
            result=self.migrate(dbpath)
            self.assertEqual(result.returncode,0,result.stderr)
            with sqlite3.connect(dbpath) as db:
                self.assertEqual(db.execute("SELECT version_num FROM alembic_version").fetchone()[0],"002_components")
                db.execute("INSERT INTO users (id,username,hashed_password,role,is_active,full_name,created_at) VALUES ('keep','keep','hash','staff',1,'',datetime('now'))")
                db.commit()
            result=self.migrate(dbpath)
            self.assertEqual(result.returncode,0,result.stderr)
            with sqlite3.connect(dbpath) as db:
                self.assertEqual(db.execute("SELECT username FROM users WHERE id='keep'").fetchone()[0],"keep")
    def test_S28_incompatible_existing_schema_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbpath=Path(tmp)/"db.sqlite"
            with sqlite3.connect(dbpath) as db:
                db.execute("CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT)")
                db.execute("INSERT INTO users VALUES ('keep','keep')")
                db.commit()
            result=self.migrate(dbpath)
            self.assertNotEqual(result.returncode,0)
            self.assertIn("Database schema mismatch: users",result.stderr)
            with sqlite3.connect(dbpath) as db:
                self.assertEqual(db.execute("SELECT username FROM users WHERE id='keep'").fetchone()[0],"keep")
                if db.execute("SELECT name FROM sqlite_master WHERE name='alembic_version'").fetchone():
                    self.assertEqual(db.execute("SELECT count(*) FROM alembic_version").fetchone()[0],0)
    def test_M22_upgrade_existing_001_preserves_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbpath=Path(tmp)/"old.sqlite"
            self.assertEqual(self.migrate(dbpath).returncode,0)
            with sqlite3.connect(dbpath) as db:
                for col in ("components","components_complete","shared_systems","concurrent_design","volume","hazard_class","industrial_subtype"):
                    db.execute(f"ALTER TABLE project_data DROP COLUMN {col}")
                db.execute("UPDATE alembic_version SET version_num='001_v11'")
                fields=[];values=[]
                for _,name,kind,required,default,pk in db.execute("PRAGMA table_info(project_data)"):
                    if required or pk:
                        fields.append(name)
                        values.append(0 if kind in ('FLOAT','INTEGER') else '2026-01-01 00:00:00' if 'DATE' in kind else 'oldproject' if name=='id' else 'Sabaco cũ' if name=='name' else 'Nhà xưởng' if name=='type' else 'keep')
                db.execute('INSERT INTO project_data ('+','.join(fields)+') VALUES ('+','.join('?' for _ in fields)+')',values)
                db.commit()
            result=self.migrate(dbpath)
            self.assertEqual(result.returncode,0,result.stderr)
            with sqlite3.connect(dbpath) as db:
                row=db.execute("SELECT name,type,components FROM project_data WHERE id='oldproject'").fetchone()
                self.assertEqual(row,('Sabaco cũ','Nhà xưởng',None))
                self.assertEqual(db.execute("SELECT version_num FROM alembic_version").fetchone()[0],'002_components')
if __name__=="__main__":unittest.main(verbosity=2)
