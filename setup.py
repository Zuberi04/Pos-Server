from pathlib import Path
import ast
from importlib.metadata import PackageNotFoundError, metadata
from subprocess import CalledProcessError, run

from utils.extras import clean_str


class UpdateReqs:

    def __init__(self):
        self.dists = []
        self.output_path = Path(__file__).parent.resolve() / "sys_logs"
        self.output_path.mkdir(exist_ok=True)
        self.output_path = self.output_path / "unused_pkg.txt"
        self.path = Path(__file__).parent.resolve().parent
        if self.path.is_dir():
            self.path = self.path / ".venv"
        elif not Path(self.path / "pyvenv.cfg").is_file():
            raise FileNotFoundError("Venv directory does not contain env file!!")
        self.target = [
            "version",
            "name",
            "title",
            "requires-Dist",
            "dependency",
        ]

    def audit_installed_pkgs(self, top_l: set = set(), checked: list[Path] = []):
        path = self.path.parent / "server"

        def walk_file(a: Path):
            tree = ast.parse(a.read_bytes(), a.name)
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            top_l.add(alias.name.split(".")[0])
                elif node.level == 0 and node.module:
                    top_l.add(node.module.split(".")[0])
            return None

        def check_within_dir(p: Path):
            for a in p.iterdir():
                if not a.name.startswith("__"):
                    if not a.is_dir():
                        if a.is_file() and a.name.endswith(".py"):
                            walk_file(a)
                    elif a not in checked:
                        return check_within_dir(a)
            return p

        if not path.is_dir() or path.name.find("ser") == -1:
            raise ValueError(
                f"Error: path not a dir or path not of server dir with path: {path}!!"
            )
        print(f"Walking path with url: {path}")
        for d in path.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                checked.append(check_within_dir(d))
                while d not in checked:
                    checked.append(check_within_dir(d))
            elif d.is_file() and d.name.endswith(".py"):
                walk_file(d)
        print(f"Top_level packages with len: {len(top_l)}")
        if not self.output_path.is_file():
            run(
                f"cd {path} && fawltydeps --check-unused > {self.output_path}",
                shell=True,
            )
        else:
            from time import time

            m = time() - self.output_path.stat().st_mtime
            if m >= self.output_path.stat().st_mtime + (7 * 24 * 3600):
                run(
                    f"cd {path} && fawltydeps --check-unused >> {self.output_path}",
                    shell=True,
                )

        return self.update_requirements(self.output_path, top_l)

    def _check_if_unused_is_dep(self, unused: list[str], top_l: set):
        if self.dists:
            self.find_within_dependencies(unused, top_l)
            for dist in self.dists:
                for k in dist.keys():
                    if isinstance(self._check_usability(unused, k), int):
                        unused = self._peruse_through_dists(dist[k], unused)
        print(f"Length to to rm: \n{unused}")
        return unused

    def select_independent_pkgs(
        self, top_l: set, unused: list, valid: bool = False, packages: list = []
    ):
        for pkg in self.dists:
            for k in pkg.keys():
                if isinstance(self._check_usability(unused, k), int):
                    for n_pkg in self.dists:
                        if n_pkg != pkg:
                            if not k in n_pkg:
                                for m in n_pkg.keys():
                                    if isinstance(
                                        self._check_usability(unused, m), int
                                    ):
                                        for item in n_pkg[m]:
                                            if self.compare_values(
                                                self.format_q(k), item
                                            ):
                                                valid = (
                                                    not valid if not valid else valid
                                                )
                            else:
                                pkg[k].extend(
                                    [
                                        (
                                            n
                                            if not isinstance(n, list)
                                            else pkg[k].extend(n)
                                        )
                                        for n in n_pkg[m]
                                        if n not in pkg[k]
                                    ]
                                )
                if not valid or self.format_q(k) in top_l and pkg not in packages:
                    packages.append(pkg)
        return packages

    @staticmethod
    def format_q(y: str):
        return (
            y.split(".")[0][
                : (
                    -2
                    if y.split(".")[0][-2] == "-" and y.split(".")[0][-1].isnumeric()
                    else -1
                )
            ]
            if y.find(".") != -1
            else y
        )

    def find_within_dependencies(self, unused: list, top_l: set):
        print(f"Dists before filtration: {len(self.dists)}")
        packages = self.select_independent_pkgs(top_l, unused)
        for pkg in self.dists:
            n_pkg = self.dists[
                (
                    self.dists.index(pkg) + 1
                    if self.dists.index(pkg) < len(self.dists) - 1
                    else 0
                )
            ]
            if pkg or n_pkg not in packages:
                if pkg != n_pkg:
                    for k, v in pkg.items():
                        if not k in n_pkg:
                            for x in n_pkg.keys():
                                if v != n_pkg[x]:
                                    for deps in n_pkg[x]:
                                        if deps in v:
                                            for dep in v:
                                                if deps != dep:
                                                    if self.compare_values(
                                                        self.format_q(x), clean_str(dep)
                                                    ):
                                                        v.extend(
                                                            [
                                                                (
                                                                    n
                                                                    if not isinstance(
                                                                        n, list
                                                                    )
                                                                    else v.extend(n)
                                                                )
                                                                for n in n_pkg[x]
                                                                if n not in v
                                                            ]
                                                        )
                                                        if n_pkg in self.dists:
                                                            self.dists.remove(n_pkg)
                                        elif self.compare_values(
                                            self.format_q(k), clean_str(deps)
                                        ):
                                            v.extend(
                                                [
                                                    (
                                                        n
                                                        if not isinstance(n, list)
                                                        else n_pkg[x].extend(n)
                                                    )
                                                    for n in v
                                                    if n not in n_pkg[x]
                                                ]
                                            )
                                            if pkg in self.dists:
                                                self.dists.remove(pkg)
                                else:
                                    self.dists.remove(n_pkg)
                else:
                    for k in pkg.keys():
                        if self.format_q(k) not in top_l or not isinstance(
                            self._check_usability(unused, k), int
                        ):
                            self.dists.remove(pkg)
                            break
        return print(f"Length of dist after filtration: {len(self.dists)}")

    def _peruse_through_dists(self, dist: list, unused: list):
        for x in dist:
            if isinstance(x, str):
                for u in unused:
                    if self.compare_values(clean_str(x), clean_str(u)):
                        unused.remove(u)
            else:
                dist.extend(x)
        return unused

    def compare_values(self, a: str, b: str):
        def format_a_in_form_of_b(x: str, y: str, z: str = ""):
            for c in y:
                z = z + c if c in x or c in ("-", "_") else z
            return z

        if len(a) >= len(b):
            if a != b and a.find(b) == -1:
                if a.find(b[:3]) != -1 and a.find(b[-3:]) != -1:
                    if not a.index(b[0]) or a[a.index(b[0]) - 1] == " ":
                        a = format_a_in_form_of_b(a[a.index(b[0]) :], b)
                        print(f"Formatted {a} for comparing to -> {b}")
                        if len(a) >= len(b) and a == b or a.find(b) != -1:
                            return True
                return False
            return True
        return self.compare_values(b, a)

    @staticmethod
    def _check_usability(data: list, k: str, y: int = 1):
        while y < len(k) and isinstance(y, int):
            if k[:y] in data:
                return k
            y += 1
        return y

    def _compare_deps(self, path: Path, reqs: list[str], top_l: set):
        if not path or not path.is_file() or not reqs:
            return None if not reqs else reqs
        with path.open("r") as r:
            unused = r.readlines()
            if not unused:
                try:
                    run(
                        f"cd {self.path.parent / 'server'} && fawltydeps --check-unused > {self.output_path}",
                        shell=True,
                    ).check_returncode()
                except CalledProcessError:
                    run(
                        f"cd {self.path.parent / 'server'} && pip install fawltydeps",
                        shell=True,
                    ).check_returncode()
                return self._compare_deps(path, reqs, top_l)
            unused = [
                clean_str(self._return_alphaed_query(u))
                for u in unused
                if u.startswith("-")
            ]
            print(f"Length of unused: {len(unused)}")
            unused = self._check_if_unused_is_dep(unused, top_l)
            if unused:
                for r in reqs:
                    for u in unused:
                        if self.compare_values(clean_str(r), clean_str(u)):
                            reqs = [x for x in reqs if x != r]
                            unused = [y for y in unused if y != u]
            print(f"Unused remaining after cleanup: {unused}")
            return reqs

    def update_requirements(self, path: Path, top_l: set):
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
            reqs = self._compare_deps(path, reqs, top_l)
            if not reqs:
                raise ValueError("Error, failed to compare reqs")
            req.write_text(f"{reqs[0]}\n")
            reqs = [r for r in reqs if reqs.index(r)]
            for r in reqs:
                with req.open("a") as w:
                    l = w.write(f"{r}\n")
                    if not isinstance(l, int):
                        raise ValueError("Error: Failed to write requirement data!!")
                reqs = [s for s in reqs if s != r]
            try:
                run(
                    f"cd {self.path.parent / 'server'} && pip install --dry-run --ignore-installed -r requirements.txt",
                    shell=True,
                ).check_returncode()
            except CalledProcessError:
                raise CalledProcessError
                # return self.audit_installed_pkgs()
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
                                        and not pkg.name.startswith(("_", "pip"))
                                    ):
                                        try:
                                            meta = metadata(pkg.name)
                                            if meta["Name"]:
                                                reqs = self._check_if_found(
                                                    meta["Name"]
                                                    + ">="
                                                    + meta["Version"],
                                                    reqs,
                                                    meta["Require-Dist"],
                                                )
                                        except Exception:
                                            meta = self._search_for_nxt_module(
                                                pkg, site, used
                                            )
                                            if not isinstance(meta, list):
                                                used = meta[-1]
                                                if not isinstance(meta[0], Path):
                                                    if "Name" and "Version" in meta[0]:
                                                        reqs = self._check_if_found(
                                                            meta[0]["Name"]
                                                            + ">="
                                                            + meta[0]["Version"],
                                                            reqs,
                                                            meta["Require-Dist"],
                                                        )
                                                        continue
                                                    else:
                                                        pkg = meta[-2]
                                                else:
                                                    pkg = meta[0]
                                            else:
                                                used = meta
                                            req = ">="
                                            if pkg.is_dir():
                                                for p in pkg.iterdir():
                                                    if p.is_file():
                                                        if p.name.startswith(
                                                            ("META", "__init__")
                                                        ):
                                                            with p.open("r") as file:
                                                                for l in file:
                                                                    if (
                                                                        not l.isidentifier()
                                                                    ):
                                                                        for (
                                                                            t
                                                                        ) in (
                                                                            self.target
                                                                        ):
                                                                            t = (
                                                                                (
                                                                                    "__"
                                                                                    + t
                                                                                    + "__"
                                                                                )
                                                                                if p.name.startswith(
                                                                                    "__"
                                                                                )
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
                                                                                    self.add_to_dists(
                                                                                        pkg.name,
                                                                                        l,
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
                                                                            req, reqs
                                                                        )
        return reqs

    def _check_if_found(self, req: str, reqs: list[str], dist: str = None):
        if req not in reqs:
            reqs.append(req)
            if dist:
                self.add_to_dists(clean_str(req.split(">=")[0]), dist)
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
        return "".join([char for char in x if char.isalnum()]).strip()

    def add_to_dists(self, pkg_name: str, dist: str | list):
        if self.dists:
            for item in self.dists:
                for k in item.keys():
                    if (
                        k.startswith(pkg_name)
                        or pkg_name.startswith(k)
                        and dist not in item[k]
                    ):
                        return (
                            item[k].extend(dist)
                            if not isinstance(dist, str)
                            else item[k].append(dist)
                        )
        return self.dists.append({pkg_name: [dist] if isinstance(dist, str) else dist})


update_reqs = UpdateReqs()
