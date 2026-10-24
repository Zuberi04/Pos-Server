from pathlib import Path
from importlib.metadata import PackageNotFoundError, metadata
from subprocess import run


class UpdateReqs:
    def __init__(self):
        self.dists = []
        self.output_path = Path(__file__).parent.resolve() / "sys_logs"
        self.output_path.mkdir(exist_ok=True)
        self.output_path = self.output_path / "unused_pkg.txt"
        self.path = Path(__file__).parent.resolve().parent
        if not self.path.is_dir():
            return print("Error: Prod env failed to find root dir!! ")
        self.path = self.path / ".venv"
        if not Path(self.path / "pyvenv.cfg").is_file():
            return print("Path not of virtual-env!!")
        self.target = [
            "version",
            "name",
            "title",
            "requires-Dist",
            "dependency",
        ]

    def audit_installed_pkgs(self):
        path = self.path.parent / "server"
        if not path.is_dir() or path.name.find("ser") == -1:
            raise ValueError(
                f"Error: path not a dir or path not of server dir with path: {path}!!"
            )
        elif not self.output_path.is_file():
            run(
                f"cd {path} && fawltydeps --check-unused > {self.output_path}",
                shell=True,
            )
        else:
            import time

            m = time.time() - self.output_path.stat().st_mtime
            if m >= self.output_path.stat().st_mtime + (7 * 24 * 3600):
                run(
                    f"cd {path} && fawltydeps --check-unused >> {self.output_path}",
                    shell=True,
                )
        return self.update_requirements(self.output_path)

    def _check_if_a_dep(self, unused: list[str], valid: bool = False):
        if not self.dists:
            raise ValueError("Failed to get dist for dependency comparison!!")
        "[x]s some of x exist in [y]s if exist as key then y removes if as values the remains in x else x removes"
        for u in unused:
            for dist in self.dists:
                for k in dist.keys():
                    if k.find(".") != -1:
                        k = k.split(".")[0]
                    elif k not in unused:
                        if u in dist[k]:
                            valid = True
                    else:
                        self.dists = [d for d in self.dists if d != dist and not k in d]
            if valid or u.endswith("corn"):
                unused.remove(u)
        print(f"Length of analyzed unused: {len(unused)}")
        return unused

    def _compare_deps(self, path: Path, reqs: list[str]):
        if not path or not path.is_file() or not reqs:
            return None if not reqs else reqs
        with path.open("r") as r:
            unused = r.readlines()
            if not unused:
                raise ValueError(f"Failed to read file in path: {path}!!")
            from utils.extras import clean_str

            unused = [
                clean_str(u.replace("-", ""))[1:-1] for u in unused if u.startswith("-")
            ]
            print(f"Length of unused: {len(unused)}")
            unused = self._check_if_a_dep(unused)
            if unused:
                for u in unused:
                    for r in reqs:
                        if r.startswith(u):
                            reqs.remove(r)
            return reqs

    def update_requirements(self, path: Path):
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
            data = [d.replace("\n", "").strip() for d in data]
            reqs = self._check_through_venv_dir()
            if not reqs or reqs is None:
                return print("No update required for packages!!")
            reqs = self._compare_deps(path, reqs)
            if not reqs:
                raise ValueError("Error, failed to compare reqs")
            # print(f"Requirements: {reqs}")
            req.write_text(f"{reqs[0]}\n")
            reqs = [r for r in reqs if reqs.index(r)]
            for r in reqs:
                if reqs.count(r) > 1:
                    reqs.remove(r)
                else:
                    with req.open("a") as w:
                        l = w.write(f"{r}\n")
                        if not isinstance(l, int):
                            raise ValueError(
                                "Error: Failed to write requirement data!!"
                            )
            return print(
                f"Updated requirements file with a size of: {req.stat().st_size / 1024}kb!!"
            )

    @staticmethod
    def _check_existence_of_x_in_y(x: str, y: str, target: bool = False):
        if x in y or y in x:
            if not target:
                return True
            elif y.startswith(x) or x.startswith(y):
                return True
        return False

    def _search_for_nxt_module(self, pkg: Path, site: Path, used: list[str] = []):
        if not site:
            raise ValueError(f"Error: Failed to get all params for search routine!!")
        elif pkg.name not in used:
            used.append(pkg.name)
        for p in site.iterdir():
            if p.name.find(pkg.name) != -1 and pkg.name != p.name:
                if p.name not in used:
                    used.append(p.name)
                try:
                    return (metadata(p.name), p, used)
                except PackageNotFoundError:
                    if p.name.endswith("-info"):
                        return (p, used)
        return used

    def _check_through_venv_dir(self, reqs: list[str] = [], used: list[str] = []):
        for v in self.path.iterdir():
            if v.name == "lib":
                if not v.is_dir():
                    raise ValueError(
                        f"Error: Venv package is not of root dir with path: {v}"
                    )
                for x in v.iterdir():
                    if x.name.find("python") != -1:
                        if not x.is_dir():
                            raise ValueError("Error: python path is not of directory!!")
                        for site in x.iterdir():
                            if site.is_dir():
                                for pkg in site.iterdir():
                                    if (
                                        pkg.name not in used
                                        and not pkg.name.startswith("_")
                                        and not pkg.name.startswith("pip")
                                    ):
                                        try:
                                            meta = metadata(pkg.name)
                                            if meta["Name"]:
                                                reqs = self._check_if_found(
                                                    meta["Name"]
                                                    + ">="
                                                    + meta["Version"],
                                                    reqs,
                                                    meta.get("Require-Dist"),
                                                )
                                        except Exception:
                                            meta = self._search_for_nxt_module(
                                                pkg, site, used
                                            )
                                            if not isinstance(meta, list):
                                                used = meta[len(meta) - 1]
                                                if not isinstance(meta[0], Path):
                                                    if "Name" in meta[0]:
                                                        reqs = self._check_if_found(
                                                            meta[0]["Name"]
                                                            + ">="
                                                            + meta[0]["Version"],
                                                            reqs,
                                                            meta[0].get("Require-Dist"),
                                                        )
                                                        continue
                                                    else:
                                                        pkg = meta[1]
                                                else:
                                                    pkg = meta[0]
                                            else:
                                                used = meta
                                            req = ">="
                                            if pkg.is_dir():
                                                x = (
                                                    "META"
                                                    if pkg.name.endswith("-info")
                                                    else "__in"
                                                )
                                                for p in pkg.iterdir():
                                                    if p.is_file():
                                                        if p.name.startswith(x):
                                                            with p.open("r") as file:
                                                                for l in file:
                                                                    for (
                                                                        t
                                                                    ) in self.target:
                                                                        t = (
                                                                            (
                                                                                "__"
                                                                                + t
                                                                                + "__"
                                                                            )
                                                                            if "_" in x
                                                                            else t[
                                                                                0
                                                                            ].upper()
                                                                            + t[1:]
                                                                        )
                                                                        if self._check_existence_of_x_in_y(
                                                                            t,
                                                                            l,
                                                                            True,
                                                                        ):
                                                                            if t.startswith(
                                                                                (
                                                                                    "Req",
                                                                                    "req",
                                                                                )
                                                                            ):
                                                                                if (
                                                                                    pkg.name
                                                                                    in self.dists
                                                                                ):
                                                                                    i = self.dists.index(
                                                                                        pkg.name
                                                                                    )
                                                                                    self.dists[
                                                                                        i
                                                                                    ].append(
                                                                                        l
                                                                                    )
                                                                                else:
                                                                                    self.dists.append(
                                                                                        {
                                                                                            pkg.name: [
                                                                                                l
                                                                                            ]
                                                                                        }
                                                                                    )
                                                                            else:
                                                                                req = self._formart_found_item_of_req(
                                                                                    t,
                                                                                    l,
                                                                                    req,
                                                                                )
                                                                if (
                                                                    not req.startswith(
                                                                        (">=", "_", "-")
                                                                    )
                                                                    and not req.endswith(
                                                                        (">=", "_", "-")
                                                                    )
                                                                    and len(
                                                                        req.split(">=")
                                                                    )
                                                                    == 2
                                                                ):
                                                                    if (
                                                                        len(
                                                                            req.split(
                                                                                ">="
                                                                            )[0]
                                                                        )
                                                                        <= 20
                                                                        and not req[
                                                                            0
                                                                        ].isnumeric()
                                                                    ):
                                                                        reqs = self._check_if_found(
                                                                            req,
                                                                            reqs,
                                                                        )

        return reqs

    def _check_if_found(self, req: str, reqs: list[str], dist: str = None):
        if dist:
            if req.split(">=")[0] in self.dists:
                i = self.dists.index(req.split(">=")[0])
                self.dists[i].append(dist)
            else:
                self.dists.append({req.split(">=")[0]: [dist]})
            for r in reqs:
                r = r.split(">=")[0]
                if r or r.lower() in dist:
                    reqs.remove(r)
        elif req not in reqs:
            reqs.append(req)
        return reqs

    @staticmethod
    def _formart_found_item_of_req(flag: str, item: str, req: str):
        item = item.replace(flag, "").strip()
        if item.startswith(("'", '"')):
            item = item[1:-1]
        elif flag.endswith("sion"):
            if item.find(".") == -1 or item.count(".") > 3:
                return req
            return req + "".join([i for i in item if i.isnumeric() or i == "."])
        return "".join([i for i in item if i.isalnum() or i in ["-", "_"]]) + req

    @staticmethod
    def _return_alphaed_query(x: str):
        return "".join([char for char in x if char.isalnum()])


update_reqs = UpdateReqs()
