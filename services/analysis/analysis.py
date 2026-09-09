from networkx import Graph

from services.analysis.priority import queue, priority_queue
from r_services.service import r_service
from utils.extras import create_user_cache_key, decode_json_objects
from utils.similarity import Queue


class AnalyzeGraph:
    def __init__(self):
        self.why = {
            "centrality": "Common sale",
            "closeness": "Uncommon sale",
            "al_con": "Approximated equality btw two or more sales",
            "betweeness": "Interval sales between centrality sales",
        }

    def analyze_graph(self, graph: Graph, id: str):
        # assign node data to priority based on conn, closeness, centrality, weight and btwness
        if not graph:
            raise ValueError("Graph not passed for analysis!!")
        for n in graph.nodes(data=True):
            p_xhics = self.beam_odd_attr(n[1])
            if not p_xhics:
                continue
            infered = self.infer_algebra_con(n, graph, p_xhics)
            if not infered is None:
                if not isinstance(infered, dict):
                    if n != infered:
                        weight = self.infer_weight_from_edge_attr(infered, graph)
                        if not weight:
                            continue
                        queue.push(
                            self.calculate_priority_value(weight, infered[1][p_xhics]),
                            (infered, str(graph[infered]).encode("utf-8")),
                        )
                        continue
                    weight = self.infer_weight_from_edge_attr(n, graph)
                    if not weight:
                        continue
                    queue.push(
                        self.calculate_priority_value(weight, n[1][p_xhics]),
                        (n, str(graph[n]).encode("utf-8")),
                    )
                    continue
                p_k = None
                for k, v in infered.items():
                    if p_k is None:
                        p_k = k
                    elif p_k == k:
                        break
                    weight = self.infer_attr_of_node_edge(v, graph)
                    if not weight:
                        continue
                    queue.push(
                        self.calculate_priority_value(weight, v[1][p_xhics]),
                        (v, str(graph[v]).encode("utf-8")),
                    )
                    continue
                continue
            weight = self.infer_attr_of_node_edge(n, "weight", graph)
            if not weight:
                continue
            queue.push(
                self.calculate_priority_value(weight, n[1][p_xhics]),
                (n, str(graph[n]).encode("utf-8")),
            )
            continue
        records = self.analyze_queue_to_readable_format(queue)
        return self.why_node_occurred_from_analysis(records, graph, id)

    def infer_algebra_con(node: tuple, graph: Graph, p_xhics: str):
        for n in graph.nodes(data=True):
            if node == n:
                continue
            elif not p_xhics in n[1]:
                continue
            elif node[1][p_xhics] != n[1][p_xhics]:
                if node[1][p_xhics] > n[1][p_xhics]:
                    return node
                return n
            return {"act_n": node, "nxt_n": n}
        return None

    @staticmethod
    def infer_weight_from_edge_attr(node, graph: Graph):
        edges = graph.edges(node, data=True)
        for e in edges:
            if not "profit" or not "rate" in e[2]:
                raise ValueError("Error, missing data from node attr")
            return e[2]["profit"] * e[2]["rate"]
        return None

    @staticmethod
    def calculate_priority_value(weight: float, p: float):
        return weight * p

    @staticmethod
    def beam_odd_attr(attr: dict):
        odds = ["al_con", "betweeness", "closeness", "centrality"]
        q = Queue()

        for k in attr.keys():
            if k not in odds:
                continue
            elif not q.__len__():
                q.push(k)
                continue
            prev = q.pop()
            if odds.index(k) >= odds.index(prev):
                if attr[k] >= attr[prev]:
                    l = odds.index(k) - odds.index(prev)
                    if l > 1:
                        q.push(prev)
                        continue
                    q.push(k)
                    continue
                q.push(prev)
                continue
            q.push(k)
            continue

        return q.pop()

    @staticmethod
    def analyze_queue_to_readable_format(queue: priority_queue):
        if queue.__len__ <= 0:
            raise ValueError('Error, failed to travers graph!!')
        result = []
        while queue.__len__ > 0:
            p, (n, en_n) = queue.pop()
            flow = en_n.decode("utf-8")
            res = {"influence": p}
            for prop in flow:
                if prop in n:
                    if not isinstance(prop, dict):
                        res["product"] = prop
                        continue
                    pass
                elif not isinstance(prop, dict):
                    res["relation"] = prop
                elif res not in result:
                    result.append(res)
                break
            continue
        # sorts analysis via most influence sale
        records = []
        for res in result:
            if not len(records):
                records.append(res)
                continue
            for rec in records:
                if res != rec:
                    if res["influence"] > rec["influence"]:
                        i = records.index(rec)
                        if res not in records:
                            records.insert(i, res)
                        break
                    continue
                continue
            continue
        return records

    def why_node_occurred_from_analysis(self, records: list, graph: Graph, id: str):
        analysis = records
        for record in analysis:
            if record["product"]:
                if record["product"] in graph:
                    node = graph[record["product"]].items()
                    for n, data in node:
                        for k, v in data.items():
                            if k in self.why:
                                why = self.why[k]
                                reason = self.generate_why(why, record, id)
                                if not reason:
                                    raise ValueError(
                                        "Error, failed to gen reason why node occurred!!"
                                    )
                                if not "why" in data:
                                    data["why"] = reason
                                data["why"] = data["why"] + " " + reason
                                node[1] = data
                                continue
                            continue
                        break
                    graph[record["product"]] = node
                    continue
                raise ValueError(
                    f"Error, product with value: {record['product']} not found in graph!!"
                )
            analysis.remove(record)
        return {"analysis": records, "graph": graph}

    def generate_why(self, why: str, record: dict, id: str):
        prev = r_service.collect_cache(create_user_cache_key(id))
        if not prev or not "analysis" in prev:
            return self.generate_insights(record, why)
        analysis = decode_json_objects(prev["analysis"])
        for prev in analysis:
            if not prev or not isinstance(prev, dict):
                raise ValueError(
                    f"Error, cached data not found or invalid type of: {type(prev)}!!"
                )
            elif prev["product"] != record["product"]:
                continue
            elif prev["influence"] != record["influence"]:
                return self.generate_insights(
                    record, why, (record["influence"] - prev["influence"])
                )
            break
        return self.generate_insights(record, why)

    @staticmethod
    def generate_insights(record: dict, why: str, diff: float = None):
        if diff:
            return f"{why} with an influence of {record['influence']} having a diff of {diff} to previous sales"
        return f"{why} with an influence of {record['influence']}"


graph_anlys = AnalyzeGraph()
