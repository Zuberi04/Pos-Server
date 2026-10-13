class EstimateCOG:
    "C.O.G: assumption being that a good makes a profit of 190% of its 100% cog. Thus C.O.G can be calculated from its R.P"

    "P max point: MR = MC"
    "S => MR > MC"

    def __init__(self):
        "Max Pr => COGs + 1.90 * COGs = 2.90 * COGs"
        "Mode Pr => COGs + 1.00 * COGs = 2.00 * COGs"
        "Min Pr => MaxPr / ModePr + 1.00 * COGs"
        self.eff = {"max": 2.90, "mode": 2.00, "min": 2.90 / 2.00 + 1}

    def parse_cog(self, cog: float, data: dict, parsed: bool = False):
        "Max Pr = COGs(1) + 1.20 * COGs = 2.20 * COGs"
        for k in self.eff.keys():
            if cog * self.eff[k] < data["price"]:
                if cog * self.eff[k] + cog * self.eff[k] * 0.2 == data["price"]:
                    parsed = True
                    break
            else:
                parsed = True
                break
        if not parsed:
            raise ValueError(f"Failed to pass cog of {cog} to price: {data['price']}")
        print("Estimated COG proved within rule of estimate")
        data["amount"] = cog
        return data

    def calculate_cog_from_r_price(self, data: dict):
        if not "price" in data:
            raise ValueError("Error, data not of C.O.G calculation!!")
        cog = 0
        for k in self.eff.keys():
            cog += data["price"] / self.eff[k]
        cog /= len(self.eff)
        return self.parse_cog(cog, data)


est_price = EstimateCOG()
