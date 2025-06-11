import json


with open("medal.json", "r", encoding="utf-8") as f:
    data = json.load(f)


res = []
for i in data["data"]:
    if data["data"][i]["section"] != "step":
        res.append(
            {
                "name": i,
                "image": data["data"][i]["image"],
            }
        )

with open("epic.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=4)
