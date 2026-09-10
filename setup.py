from pathlib import Path
from importlib.metadata import version


def update_requirements():
    req = Path("requirements.txt")
    if not req.is_file():
        raise FileNotFoundError(f"Error: file not found or path not of file {req}!!")

    reqs = []
    with req.open("r") as r:
        data = r.readlines()
        if not data:
            raise ValueError(
                f"Error: server dependencies not found with err-data: \t {data}!!"
            )
        data = _check_through_venv_dir(data)
        for d in data:
            while ">=" not in d:
                if " " in d:
                    d = d.replace(" ", "").strip()
                elif "==" in d:
                    d = d.replace("=", ">")
            if d not in reqs:
                reqs.append(d)

    with req.open("w") as w:
        w.writelines(reqs)

    return None


def _check_through_venv_dir(reqs: list[str]):
    venv = Path(".venv")
    if not venv.is_dir():
        raise ValueError(f"Error: Venv env is not of root dir with path: {venv}")
    for v in venv.iterdir():
        if v.name.find("lib") != -1:
            if not v.is_dir():
                raise ValueError(f"Error: Venv env is not of root dir with path: {v}")
            for x in v.iterdir():
                found = False
                if x.name.find(".dist") == -1:
                    if x not in reqs:
                        for r in reqs:
                            if r.find(x.name) != -1 or x.name.startswith(r[:4]):
                                found = True
                                break
                        if not found:
                            req = x.name + ">=" + version(x.name)
                            if req not in reqs:
                                reqs.append(req)
    return reqs
