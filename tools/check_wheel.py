"""Run installed-package smoke checks outside the repository, without templates."""
from pathlib import Path
import json,os,subprocess,sys,tempfile


def main():
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='gjb-wheel-') as folder:
        work=Path(folder);wheels=work/'wheels';target=work/'installed'
        subprocess.run([sys.executable,'-m','pip','wheel','--no-deps','--no-build-isolation','-w',str(wheels),str(root/'skills/gjb438c-md-first')],check=True)
        wheel=next(wheels.glob('*.whl'))
        subprocess.run([sys.executable,'-m','pip','install','--no-deps','--no-index','--target',str(target),str(wheel)],check=True)
        env=dict(os.environ,PYTHONPATH=str(target))
        code='''from pathlib import Path
from gjb438c_suite.cli import main
from gjb438c_suite.registry import iter_document_types,default_front_matter_template
import gjb438c_suite
assert str(Path(gjb438c_suite.__file__).resolve()).startswith(str(Path("installed").resolve()))
assert gjb438c_suite.__version__=="0.4.0"
assert default_front_matter_template().is_file()
for item in iter_document_types():
    assert main(["init","--type",item.code,"--output",item.code+".md"])==0
assert len(list(Path('.').glob('*.md')))==20
assert main(["render","OCD.md","--profile=draft","--output","OCD.docx"])==0
assert main(["import-word","OCD.docx","--output","returned.md"])==0
assert Path("OCD.md").read_bytes()==Path("returned.md").read_bytes()
print("INSTALLED_WHEEL_SMOKE_PASSED")
'''
        subprocess.run([sys.executable,'-c',code],cwd=work,env=env,check=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
