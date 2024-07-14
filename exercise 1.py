import requests



class One_Task:
    def __init__(self):
        self.url = "https://restcountries.com/v3.1/independent?status=true"
        self.params = {"fields": ["name", "capital", "coatOfArms"]}

    def get_results(self):
        try:
            response = requests.get(self.url, params=self.params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            return str(e)

    def join(self):
        countrys = self.get_results()
        return "\n".join(
            [
                f"{country['name']['common']} \t {country['capital'][0]} \t {country['coatOfArms']['png']}"
                for country in countrys
            ]
        )


