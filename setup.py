from pathlib import Path
from importlib.metadata import version, requires, PackageNotFoundError


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
            w.writelines("\n".join(reqs) + "\n")

        # w.writelines(reqs)

    return print(f"Updated requirements file with len: {len(reqs)}!!")


def _check_through_venv_dir(reqs: list[str]):
    root = Path(__file__).resolve().parent
    if not root:
        raise ModuleNotFoundError("Error: Root module not found!!")
    venv = root / ".venv"
    if not venv.is_dir():
        raise ValueError(f"Error: Virtual environment does not exist {venv}")
    elif not (venv / "pyvenv.cfg").is_file():
        raise ValueError("Error: Dir is not of python virtual environment!!")
    raw = []
    for v in venv.iterdir():
        if v.name.find("lib") != -1:
            if not v.is_dir():
                raise ValueError(
                    f"Error: Venv package is not of root dir with path: {v}"
                )
            for x in v.iterdir():
                if x.name.find("python") != -1:
                    if not x.is_dir():
                        raise ValueError("Error: python path is of directory!!")
                    for site in x.iterdir():
                        if not site.is_dir():
                            raise ValueError("Error: python path is not of directory!!")
                        for pkg in site.iterdir():
                            if pkg.as_uri().find(".dist") != -1:
                                continue
                            elif not pkg.name.startswith("__"):
                                print(f"Package name: {pkg.name}")
                                try:
                                    dependecies = requires(pkg.name)
                                except PackageNotFoundError as e:
                                    print(
                                        f"Module found with no metadata with err-value: \n\t{e}!!"
                                    )
                                    continue
                                if dependecies:
                                    for d in dependecies:
                                        if d in reqs:
                                            reqs.remove(d)
                                req = pkg.name + "==" + version(pkg.name)
                                print(f"Checking requirment: {req}")
                                if req not in reqs:
                                    req = req.split("==")
                                    req = req[0] + ">=" + req[1]
                                    if req not in raw:
                                        raw.append(req)

    print(
        "Processed requirments with len %i and params requirements with len: %i"
        % (len(raw), len(req))
    )

    for r in raw:
        if r not in req:
            raw.remove(r)
    return raw
