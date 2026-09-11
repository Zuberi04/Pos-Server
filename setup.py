from pathlib import Path
from importlib.metadata import PackageNotFoundError, metadata
from ast import literal_eval


class UpdateReqs:
    def __init__(self):
        pass

    def update_requirements(self):
        req = Path("requirements.txt")
        if not req.is_file():
            raise FileNotFoundError(
                f"Error: file not found or path not of file {req}!!"
            )

        with req.open("r") as r:
            data = r.readlines()
            if not data:
                raise ValueError(
                    f"Error: server dependencies not found with err-data: \t {data}!!"
                )
            data = [d.replace("\n", "").strip() for d in data if data.count(d) < 1]
            reqs = self._check_through_venv_dir(data, len(data))
            if not reqs:
                return print("No update required for packages!!")
            elif len(reqs) != len(data):
                req.write_text(reqs[0], newline="\n")
                reqs = [r for r in reqs if reqs.index(r)]
            print(f"Received raw updates with len: \n{reqs}")
            for r in reqs:
                if "==" in r:
                    r = r.replace("==", ">=")
                elif ">>" in r:
                    r = r.replace(">>", ">=")
                elif ">=" in r:
                    with req.open("a") as w:
                        rm = [">=", "=", "<", "<=", ">", "=="]
                        for m in rm:
                            if r.endswith(m):
                                r = r[:-1]
                        if not r:
                            raise ValueError("Formatted r in the wrong format!!")

                        l = w.write(f"{r}\n" if reqs.index(r) else f"\n{r}\n")
                        if not isinstance(l, int):
                            raise ValueError(
                                "Error: Failed to write requirement data!!"
                            )

        return print(
            f"Updated requirements file with a size of: {req.stat().st_size / 1024}kb!!"
        )

    @staticmethod
    def _search_if_only_module(pkg: Path, site: Path):
        print(f"Searching for module...{pkg.name}")
        for p in site.iterdir():
            if pkg.name in p.name and pkg.name != p.name:
                if p.is_dir():
                    print("Found extras from site dir, !!")
                    return p
        return None

    def _check_through_venv_dir(self, reqs: list[str], l: int):
        root = Path(__file__).resolve().parent
        if not root:
            raise ModuleNotFoundError("Error: Root module not found!!")
        venv = root / ".venv"
        if not venv.is_dir():
            venv = root.parent / ".venv"
            if not venv.is_dir():
                raise ValueError(f"Error: Virtual environment does not exist {venv}")
        elif not (venv / "pyvenv.cfg").is_file():
            raise ValueError("Error: Dir is not of python virtual environment!!")

        for v in venv.iterdir():
            if v.name.find("lib") != -1:
                if not v.is_dir():
                    raise ValueError(
                        f"Error: Venv package is not of root dir with path: {v}"
                    )
                for x in v.iterdir():
                    if x.name.find("python") != -1:
                        if not x.is_dir():
                            raise ValueError("Error: python path is not of directory!!")
                        for site in x.iterdir():
                            if not site.is_dir():
                                raise ValueError(
                                    "Error: python path is not of directory!!"
                                )
                            for pkg in site.iterdir():
                                try:
                                    meta = metadata(pkg.name)
                                except PackageNotFoundError:
                                    only = self._search_if_only_module(pkg, site)
                                    try:
                                        name = ""
                                        if not only:
                                            if pkg.name.endswith(".dist-info"):
                                                name = pkg.name.replace(
                                                    ".dist-info", ""
                                                ).strip()
                                            else:
                                                name = pkg.name
                                        else:
                                            if only.name.endswith(".dist-info"):
                                                name = only.name.replace(
                                                    ".dist-info", ""
                                                ).strip()
                                            else:
                                                name = only.name
                                        meta = metadata(name)
                                    except PackageNotFoundError:
                                        print("Package passed to exception: ", pkg.name)
                                        if not pkg.is_dir():
                                            print("Found with value: ", pkg.name)
                                            continue
                                        req = None
                                        for p in pkg.iterdir():
                                            if pkg.name.endswith(".dist-info"):
                                                if p.name.find("META") != -1:
                                                    with p.open("r+t") as file:
                                                        for line in file:
                                                            if not line.startswith(
                                                                "Name"
                                                            ):
                                                                if line.startswith(
                                                                    "Ver"
                                                                ):
                                                                    if ":" not in line:
                                                                        continue
                                                                    req = (
                                                                        req
                                                                        + ">="
                                                                        + line.split(
                                                                            ":"
                                                                        )[1].strip()
                                                                        if req
                                                                        else ">="
                                                                        + line.split(
                                                                            ":"
                                                                        )[1].strip()
                                                                    )
                                                            else:
                                                                req = (
                                                                    line.split(":")[
                                                                        1
                                                                    ].strip()
                                                                    + req
                                                                    if req
                                                                    else line.split(
                                                                        ":"
                                                                    )[1].strip()
                                                                )
                                                        if req:
                                                            print(
                                                                "Req from metadata with value: ",
                                                                req,
                                                            )
                                                            reqs = self.check_if_found(
                                                                req, reqs
                                                            )
                                                            break
                                            elif p.is_file():
                                                if "init" in p.name:

                                                    with p.open("r+t") as file:
                                                        for line in file:
                                                            if line.startswith(
                                                                "__vers"
                                                            ):
                                                                if req is None:
                                                                    req = (
                                                                        ">="
                                                                        + line.split(
                                                                            "="
                                                                        )[1].strip()
                                                                    )
                                                                else:
                                                                    req = (
                                                                        req
                                                                        + ">="
                                                                        + line.split(
                                                                            "="
                                                                        )[1].strip()
                                                                    )
                                                            elif line.startswith(
                                                                "__tit"
                                                            ) or line.startswith(
                                                                "__name"
                                                            ):
                                                                req = (
                                                                    line.split("=")[1]
                                                                    .replace("\n", "")
                                                                    .strip("")
                                                                    + req
                                                                    if req
                                                                    else line.split(
                                                                        "="
                                                                    )[1]
                                                                    .replace("\n", "")
                                                                    .strip("")
                                                                )
                                                        if req:
                                                            req = [
                                                                r
                                                                for r in req
                                                                if r not in ['"', "'"]
                                                            ]
                                                            reqs = self.check_if_found(
                                                                "".join(req).strip(),
                                                                reqs,
                                                            )
                                    continue
                                if meta["Require-Dist"]:
                                    for d in meta["Require-Dist"]:
                                        if d in reqs:
                                            reqs = [r for r in reqs if r != d]
                                reqs = self.check_if_found(
                                    meta["Name"] + ">=" + meta["version"], reqs
                                )

        return reqs if l != len(reqs) else None

    @staticmethod
    def check_if_found(req: str, reqs: list):
        reqs = [r for r in reqs if r != req]
        reqs.append(req)
        return reqs


update_reqs = UpdateReqs()
