from pathlib import Path
from importlib.metadata import PackageMetadata, PackageNotFoundError, metadata
from subprocess import run


class UpdateReqs:
    def __init__(self):
        self.rm = [">=", "=", "<", "<=", ">", "==", ">>", '"', " " "'"]
        self.output_path = Path(__file__).parent.resolve() / "sys_logs"
        self.output_path.mkdir(exist_ok=True)
        self.output_path = self.output_path / "module_logs.txt"
        self.path = Path(__file__).parent.resolve().parent
        if not self.path.is_dir():
            return print("Error: Prod env failed to find root dir!! ")
        self.path = self.path / ".venv"
        if not Path(self.path / "pyvenv.cfg").is_file():
            return print("Path not of virtual-env!!")

    def audit_installed_pkgs(self):
        path = self.path.parent / "server"
        if not path.is_dir() or path.name.find("ser") == -1:
            raise ValueError(
                f"Error: path not a dir or path not of server dir with path: {path}!!"
            )

        output = run(
            f"cd {path} && pipdeptree >> {self.output_path}", shell=True, check=True
        )

        return (
            self.start_server_collect_run_deps(path)
            if not output.stderr
            else OSError(output.stderr.decode("utf-8"))
        )

    def start_server_collect_run_deps(self, path: Path):
        import sys

        with self.output_path.open("ab") as file:
            for mod in sorted(sys.modules):
                file.write(f"{mod}\n")
            p = self.output_path.parent / "deps-tree.json"
            return run(
                f"cd {path} && pipdeptree --json-tree >> {p}", shell=True, check=True
            )

    def update_requirements(self):
        try:
            self.audit_installed_pkgs()
        except Exception as e:
            print(e)

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
            reqs = [d.replace("\n", "").strip() for d in data]
            reqs = self._check_through_venv_dir(reqs, len(reqs))
            if not reqs or reqs is None:
                return print("No update required for packages!!")
            req.write_text(reqs[0], newline="\n")
            reqs = [r for r in reqs if reqs.index(r)]
            for r in reqs:
                while reqs.count(r) > 1:
                    reqs.remove(r)
                with req.open("a") as w:
                    for m in self.rm:
                        if m in r:
                            while m != ">=":
                                r = r.replace(m, "").strip()
                            if r.count(m) > 1:
                                if r.endswith(m) or r.startswith(m):
                                    r = r.replace(m, "").strip()

                            break
                    if r == ">=":
                        continue
                    # print(f"Found req with value: {r}")
                    l = w.write(f"{r}\n" if reqs.index(r) else f"\n{r}\n")
                    if not isinstance(l, int):
                        raise ValueError("Error: Failed to write requirement data!!")

        return print(
            f"Updated requirements file with a size of: {req.stat().st_size / 1024}kb!!"
        )

    @staticmethod
    def _check_existence_of_x_in_y(x: str, y: str):
        if y.find(x) != -1 or x.find(y) != -1:
            # print(f"Found {x} and {y} to contain similarity!!")
            if len(y) >= len(x):
                if len(y) - len(y.replace(x, "").strip()) != len(x):
                    return False
                return True
            elif len(x) - len(x.replace(y, "").strip()) != len(y):
                return False
            return True
        return False

    def _search_for_nxt_module(self, pkg: Path, site: Path, reqs: list[str]):
        for r in reqs:
            if self._check_existence_of_x_in_y(
                self._return_alphaed_query(r.split(">=")[0].lower()),
                self._return_alphaed_query(pkg.name),
            ):
                print(f"Skipping package : {pkg.name}")
                return [
                    s.name
                    for s in site.iterdir()
                    if not self._check_existence_of_x_in_y(
                        self._return_alphaed_query(s.name),
                        self._return_alphaed_query(pkg.name),
                    )
                ]

        print(f"Searching for module...{pkg.name}")
        if not site:
            raise ValueError(f"Error: Failed to get all params for search routine!!")
        for p in site.iterdir():
            if pkg.name != p.name:
                if self._check_existence_of_x_in_y(p.name, pkg.name):
                    print(f"Package found with name: {p.name}")
                    try:
                        return metadata(p.name)
                    except PackageNotFoundError:
                        print(f"No metadata-info for package with name: {p.name}")
                        if p.name.endswith("-info"):
                            print(f"Returning package with name: {p.name}")
                            return p
        return None

    def _check_through_venv_dir(self, reqs: list[str], l: int):
        for v in self.path.iterdir():
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
                                    f"Error: python path is not a directory with path: {site}!!"
                                )
                            ref = []
                            for pkg in site.iterdir():
                                target = ["version", "name", "title"]
                                if (
                                    ref
                                    and pkg.name not in ref
                                    or pkg.name.startswith("__")
                                ):
                                    print(
                                        "Package not in generated ref skipping package"
                                    )
                                    continue
                                try:
                                    meta = metadata(pkg.name)
                                    reqs = self._check_if_found(
                                        meta["Name"] + ">=" + meta["Version"],
                                        reqs,
                                        meta.get("Require-Dist"),
                                    )
                                    continue
                                except PackageNotFoundError:
                                    meta = self._search_for_nxt_module(pkg, site, reqs)
                                    if not meta is None and not isinstance(meta, Path):
                                        if not isinstance(meta, list):
                                            reqs = self._check_if_found(
                                                meta["Name"] + ">=" + meta["Version"],
                                                reqs,
                                                meta.get("Require-Dist"),
                                            )
                                        else:
                                            if len(ref):
                                                ref = [m for m in meta if m in ref]
                                            else:
                                                ref = meta
                                            print(f"Found refs with len: {len(ref)}")
                                        continue
                                    pkg = meta if meta else pkg
                                    print(f"Checking package: {pkg.name}")
                                    req = ">="
                                    if pkg.is_dir():
                                        if pkg.name.endswith("-info"):
                                            target.append("META")
                                        else:
                                            target.append("__init")
                                        for p in pkg.iterdir():
                                            if p.is_file():
                                                for t in target:
                                                    if p.name.startswith(t):
                                                        print(
                                                            f"Found file with name: {p.name}"
                                                        )
                                                        target = [
                                                            f for f in target if f != t
                                                        ]
                                                        with p.open("r+t") as file:
                                                            for t in target:
                                                                if p.name.startswith(
                                                                    "__"
                                                                ):
                                                                    t = "__" + t + "__"
                                                                else:
                                                                    t = t.capitalize()
                                                                for line in file:
                                                                    if self._check_existence_of_x_in_y(
                                                                        t, line
                                                                    ):
                                                                        req = self._formart_found_item_of_req(
                                                                            t,
                                                                            line.replace(
                                                                                t, ""
                                                                            ).strip(),
                                                                            req,
                                                                        )
                                                                        break
                                                                if (
                                                                    len(req.split(">="))
                                                                    != 2
                                                                ):
                                                                    if (
                                                                        len(
                                                                            req.split(
                                                                                ">="
                                                                            )
                                                                        )
                                                                        > 2
                                                                    ):
                                                                        raise ValueError(
                                                                            f"Error, requirement exceeded with value: {req}"
                                                                        )
                                                                    continue
                                                                else:
                                                                    reqs = self._check_if_found(
                                                                        req, reqs
                                                                    )
                                                                    break
                                                            break

                                                break
                            break

        return reqs if l != len(reqs) else None

    def _check_if_found(self, req: str, reqs: list[str], meta: PackageMetadata = None):
        print(f"Adding {req} to requirements")
        if meta:
            for d in meta:
                reqs = [
                    r
                    for r in reqs
                    if not self._check_existence_of_x_in_y(
                        self._return_alphaed_query(d.strip()),
                        self._return_alphaed_query(r.split(">=")[0].lower().strip()),
                    )
                ]

        reqs.append(req)
        return reqs

    @staticmethod
    def _formart_found_item_of_req(flag: str, item: str, req: str):
        if flag.endswith("sion"):
            return req + "".join([i for i in item if i.isnumeric() or i == "."])
        return "".join([i for i in item if i.isalnum() or i in ["-", "_"]]) + req

    @staticmethod
    def _return_alphaed_query(x: str):
        return "".join([char for char in x if char.isalnum()])


update_reqs = UpdateReqs()
