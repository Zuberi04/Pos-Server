# import matplotlib as plt
import networkx as nx


class GraphSales:
    def __init__(self):
        pass

    async def collect_req_data_for_graph(self, procs: list, data: dict):
        if not procs:
            raise ValueError("Error, no data passed for graph analysis!!")
        g_data = []
        for r in procs:
            if "rels" in r:
                if not isinstance(r["rels"], list):
                    r["rels"] = [r["rels"]]
                for x in r["rels"]:
                    if "sales" in x:
                        g_data.append(
                            self.format_graph_data(
                                {y: x[y] for y in x.keys() if y != "sales"}, x["sales"]
                            )
                        )
        return await self.plot_revenue_against_products(g_data, data)

    @staticmethod
    def calc_r_of_sale(x: int, y: int):
        return x / y * 100

    def format_graph_data(self, x: dict, y: dict, res: dict = {}):
        for k in x.copy().keys():
            if not k.endswith(("id", "ed")):
                for m in y.keys():
                    if not m.endswith(("id", "ed")):
                        if isinstance(y[m], type(x[k])):
                            if isinstance(x[k], (float, int)):
                                if isinstance(x[k], int):
                                    if not m in res:
                                        res[m] = y[m]
                                        res["rate"] = self.calc_r_of_sale(x[k], y[m])
                                else:
                                    if "rate" and not k in res:
                                        from utils.cog_pricing import est_price

                                        res[k] = x[k]
                                        res["profit"] = (
                                            y[m]
                                            - est_price.calculate_cog_from_r_price(x)[
                                                "amount"
                                            ]
                                            * res["rate"]
                                        )
                        elif isinstance(x[k], str) and not k in res:
                            res[k] = x[k]
        return res

    async def plot_revenue_against_products(self, result: list, data: dict):
        if not result or not data:
            raise ValueError("Error, data not passed for plotting")
        G = nx.DiGraph()
        # nodes
        for r in result:
            G.add_node(r["brand"], weight=r["quantity"])
            try:
                nxt = result[result.index(r) + 1]
            except IndexError:
                nxt = r
            G.add_edge(
                u_of_edge=r["brand"],
                v_of_edge=nxt["brand"],
                rate=r["rate"],
                profit=r["profit"],
                price=r["price"],
            )
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
        except:
            print("Graphiz lib could not be found!!")
            pos = nx.kamada_kawai_layout(G)
        node_sizes = []
        for node in G.nodes(data=True):
            node_sizes.append(node[1]["weight"] * (len(result) / len(node)))
        edge_widths = []
        for u, v in G.edges():
            edge = G[u][v]
            edge_widths.append((edge["price"] / edge["rate"]))
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color="purple")
        # draw edges
        nx.draw_networkx_edges(
            G,
            edge_color="black",
            width=edge_widths,
            arrows=True,
            arrowstyle="->",
            arrowSize=20,
        )
        nx.draw_networkx_labels(G, pos, font_size=12, font_weight="demibold")
        edge_labels = []
        for node in G.nodes(data=True):
            edge = G.edges(node)
            edge_labels.append(
                edge[1]["profit"] if "profit" in edge[1] else edge[2]["profit"]
            )
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

        # central values of graph
        centrality = nx.degree_centrality(G)
        nx.set_node_attributes(G, centrality, "centrality")
        # closeness to centrality
        c_central = nx.closeness_centrality(G)
        nx.set_node_attributes(G, c_central, "closeness")
        # collect betweeness values from centrality of the graph
        btw_centrality = nx.betweenness_centrality(G)
        nx.set_node_attributes(G, btw_centrality, "betweeness")
        # collect algebra connection btw nodes
        algebra_conn = nx.algebraic_connectivity(G)
        nx.set_node_attributes(G, algebra_conn, "al_con")
        print(
            f"Graph is_directed ? { G.is_directed()} with values: \n {G}",
        )
        from services.analysis.analysis import graph_anlys

        return await graph_anlys.analyze_graph(G, data["id"])


gen_graph = GraphSales()
