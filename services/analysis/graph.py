# import matplotlib as plt
import networkx as nx


from database.models import Sales, Inventory, Catalog
from utils.stmt import read_stmt
from services.analysis.analysis import graph_anlys


class AnalysisOfDb:
    def __init__(self):
        pass

    def collect_req_data_for_graph(self, data: dict):
        if not "id" in data:
            return ValueError('Error, missing id for user to collect analysis')
        inventory = read_stmt.read_stmt(Inventory, query=data["id"])
        if not inventory:
            return ValueError('Error, missing data for analysis collection!!')
        catalog: dict | list = None
        if not isinstance(inventory, list):
            catalog = read_stmt.read_stmt(Catalog, query=inventory["id"])
            if not catalog:
                raise ValueError("Error, data not found in db!!")
            return self.collect_sales(catalog)
        for rec in inventory:
            r = read_stmt.read_stmt(Catalog, query=rec["id"])
            if not r:
                raise ValueError("Error, data not found in db!!")
            elif r not in catalog:
                catalog.append(r)
            continue
        return self.collect_sales(catalog, data)

    def collect_sales(self, catalog: list | dict, data: dict):
        sales: dict | list = None
        if not isinstance(catalog, list):
            sales = read_stmt.read_stmt(Sales, query=catalog["id"])
            if not isinstance(sales, list):
                raise ValueError('Error, to few of sales data to collect analysis')
        for rec in catalog:
            r = read_stmt.read_stmt(Sales, query=rec["id"])
            if not r:
                continue
            elif r not in sales:
                sales.append(r)
            continue
        return self.analyse_sales(sales, catalog, data)

    def analyse_sales(self, sales: list, catalog: list, data: dict):
        """
        brand, r.p, profit, rate of sale, quantity
        """
        if not sales or not catalog:
            raise ValueError("Error, data sets for analysis not passed!!")
        result = []
        for sale in sales:
            if not isinstance(catalog, list):
                rec = {
                    "brand": catalog["brand"],
                    "price": catalog["price"],
                    "rate": ((sale["quantity"] / catalog["stock"]) * 100),
                    "profit": sale["amount"] - catalog["price"],
                    "quantity": sale["quantity"],
                }
                if rec not in result:
                    result.append(rec)
                continue
            for log in catalog:
                if log["id"] != sale["id"]:
                    continue
                rec = {
                    "brand": log["brand"],
                    "price": log["price"],
                    "rate": ((sale["quantity"] / log["stock"]) * 100),
                    "profit": sale["amount"] - log["price"],
                    "quantity": sale["quantity"],
                }
                if rec not in result:
                    result.append(rec)
                break
            continue

        return self.plot_revenue_against_products(result, data)

    def plot_revenue_against_products(self, result: list, data: dict):
        if not result:
            raise ValueError("Error, data not passed for plotting")
        G = nx.DiGraph()
        # nodes
        for item in result:
            G.add_node(item["brand"], weight=item["quantity"])
            try:
                nxt = result[result.index(item) + 1]
            except IndexError:
                nxt = item
            G.add_edge(
                u_of_edge=item["brand"],
                v_of_edge=nxt["brand"],
                rate=item["rate"],
                profit=item["profit"],
                price=item["price"],
            )
            continue

        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
        except:
            print("Graphiz lib couldnot be found!!")
            pos = nx.kamada_kawai_layout(G)
        node_sizes = []
        for node in G.nodes(data=True):
            s = node[1]["weight"] * 10
            if s not in node_sizes:
                node_sizes.append(s)

        edge_widths = []
        for u, v in G.edges():
            edge = G[u][v]
            edge_widths.append((edge["profit"] * edge["rate"]))

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
                edge[1]["price"] if "price" in edge[1] else edge[2]["price"]
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

        print("Graph is undirected: ", G.is_directed())
        print("Graph is directed with values: \n\t", G)

        return graph_anlys.analyze_graph(G, data["id"])


gen_graph = AnalysisOfDb()
