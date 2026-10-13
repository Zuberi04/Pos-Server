from networkx import Graph
from typing import Any

from services.analysis.priority import queue, priority_queue


class AnalyzeGraph:
    def __init__(self):
        pass

    async def analyze_graph(self, graph: Graph, id: str):
        # assign node data to priority based on conn, closeness, centrality, weight and btwness
        if not graph:
            raise ValueError("Graph not passed for analysis!!")
        for n in graph.nodes(data=True):
            beam = self.beam_odd_attr(n[1])
            if beam:
                infer = self.infer_algebra_con(n, graph, beam[1])
                while infer and not isinstance(infer, dict):
                    beam = self.beam_odd_attr(infer[1])
                    if not beam:
                        break
                    infer = self.infer_algebra_con(infer, graph, beam[1])
                if infer:
                    if isinstance(infer, dict):
                        for i in infer.keys():
                            infer[i][1]["edges"] = graph.edges(infer[i], data=True)
                            queue.push(
                                (
                                    self.infer_weight_from_edge_attr(infer[i], graph)
                                    * beam[0]
                                    if beam
                                    else self.infer_weight_from_edge_attr(
                                        infer[i], graph
                                    )
                                ),
                                infer[i],
                            )
                    else:
                        infer[1]["edges"] = graph.edges(infer, data=True)
                        queue.push(
                            (
                                self.infer_weight_from_edge_attr(infer, graph) * beam[0]
                                if beam
                                else self.infer_weight_from_edge_attr(infer, graph)
                            ),
                            infer,
                        )
                else:
                    n[1] = graph.edges(n, data=True)
                    queue.push(
                        (
                            self.infer_weight_from_edge_attr(n, graph) * beam[0]
                            if beam
                            else self.infer_weight_from_edge_attr(n, graph)
                        ),
                        n,
                    )
        return await self.analyze_queue_to_readable_format(queue, graph, id)

    @staticmethod
    def infer_algebra_con(node: tuple[Any, dict[str, Any]], graph: Graph, beam: str):
        for n in graph.nodes(data=True):
            if node != n:
                if beam in n[1]:
                    if node[1][beam] != n[1][beam]:
                        if node[1][beam] > n[1][beam]:
                            return node
                    return {"act_n": node, "nxt_n": n}
        return None

    @staticmethod
    def infer_weight_from_edge_attr(
        node: tuple[Any, dict[str, Any]], graph: Graph, w: float = 0
    ):
        edges = graph.edges(node, data=True)
        for e in edges:
            if not "profit" or not "rate" in e[2]:
                raise ValueError("Error, missing data from node attr")
            w += e[2]["profit"]
        return w

    @staticmethod
    def beam_odd_attr(attr: dict):
        odds = ["centrality", "closeness", "betweeness", "al_con"]
        q = priority_queue()
        for k in attr.keys():
            if k in odds:
                if not q:
                    q.push(attr[k] * odds.index(k), k)
                else:
                    w, p = q.pop()
                    if w < attr[k] * odds.index(k) or odds.index(p) < odds.index(k):
                        q.push(attr[k] * odds.index(k), k)
                    else:
                        q.push(w, p)
        return q.pop()

    async def analyze_queue_to_readable_format(
        self, queue: priority_queue, graph: Graph, id: str
    ):
        if not queue:
            raise ValueError("Error, failed to travers graph!!")
        result = []
        while queue:
            p, n = queue.pop()
            if not result:
                result.append({"name": n[0], "inf": p, "why": n[1]["edges"]})
            else:
                for i in range(result):
                    if p > sorted(result, key=lambda x: x[0]["inf"], reverse=True)[i]:
                        result.insert(i, {"name": n[0], "inf": p, "why": n[1]["edges"]})
                        break
                if n[0] not in result:
                    result.append({"name": n[0], "inf": p, "why": n[1]["edges"]})
        return await self.from_g_data_process_insights(result, graph, id)

    async def from_g_data_process_insights(self, records: list, graph: Graph, id: str):
        from r_services.service import r_service
        from utils.extras import decode_json_objects

        prev = await r_service.collect_cache(id, "analysis")
        if prev:
            prev = decode_json_objects(prev)
        else:
            prev = []
        for r in records:
            try:
                ins = self.generate_insights(r, prev[prev.index(r["name"])])
            except IndexError:
                ins = self.generate_insights(r)
            if ins:
                for n in graph.nodes(data=True):
                    if n[0] == r["name"]:
                        n[1]["insight"] = ins
                        break

        r_service.cache_data(id, {"analysis": records, "graph": graph})
        return graph

    @staticmethod
    def generate_insights(record: dict, prev: dict = None, res: set = set()):
        for k in record.keys():
            if not isinstance(record[k], str):
                name = record["name"].capitalize()
                if k in prev:
                    if isinstance(record[k], (float, int)):
                        res.add(
                            f"{name} had a new ratio-influence of {record[k] : prev[k]} from prev sales"
                        )
                    elif isinstance(record[k], dict):
                        if record[k] == prev[k]:
                            res.add(
                                f"{name} seems to hold sameness in graphical terms!!...if you know what i mean?"
                            )
                        else:
                            for x in record[k].keys():
                                if x in prev[k]:
                                    if record[k][x] != prev[k][x]:
                                        if isinstance(record[k][x], (float, int)):
                                            if x.endswith(("it", "te")):
                                                res.add(
                                                    f"{name} with factor {x} had a ratio diff of {record[k][x] : prev[k][x]} from its previous analysis."
                                                )
                else:
                    if not isinstance(record[k], dict):
                        if isinstance(record[k], (float, int)):
                            res.add(
                                f"{name} scored an influence of {record[k]} in terms of sales analysis!!"
                            )
                    else:
                        for x in record[k].keys():
                            if x.endswith(("it", "te")):
                                res.add(
                                    f"{name} had a {x} of {record[k][x]} thus appearing within graph regions"
                                )
        return res


graph_anlys = AnalyzeGraph()
