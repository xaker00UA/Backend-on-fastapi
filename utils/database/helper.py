def member_stat_delta(first_path, last_path, field):
    return {
        "$subtract": [
            {
                "$sum": {
                    "$map": {
                        "input": {
                            "$filter": {
                                "input": f"${first_path}",
                                "as": "member",
                                "cond": {
                                    "$in": [
                                        "$$member.account_id",
                                        {
                                            "$map": {
                                                "input": f"${last_path}",
                                                "as": "m",
                                                "in": "$$m.account_id",
                                            }
                                        },
                                    ]
                                },
                            }
                        },
                        "as": "filteredMember",
                        "in": f"$$filteredMember.statistics.all.{field}",
                    }
                }
            },
            {
                "$sum": {
                    "$map": {
                        "input": {
                            "$filter": {
                                "input": f"${last_path}",
                                "as": "member",
                                "cond": {
                                    "$in": [
                                        "$$member.account_id",
                                        {
                                            "$map": {
                                                "input": f"${first_path}",
                                                "as": "m",
                                                "in": "$$m.account_id",
                                            }
                                        },
                                    ]
                                },
                            }
                        },
                        "as": "filteredMember",
                        "in": f"$$filteredMember.statistics.all.{field}",
                    }
                }
            },
        ]
    }


def get_clan_rating_pipeline(start_day, end_day):

    return [
        {"$sort": {"timestamp": -1}},
        {"$match": {"timestamp": {"$gte": start_day, "$lte": end_day}}},
        {
            "$group": {
                "_id": "$clan_id",
                "name": {"$first": "$name"},
                "region": {"$first": "$region"},
                "tag": {"$first": "$tag"},
                "clan_id": {"$first": "$clan_id"},
                "firstClan": {"$first": "$$ROOT"},
                "lastClan": {"$last": "$$ROOT"},
            }
        },
        {
            "$addFields": {
                "general_battles": member_stat_delta(
                    "firstClan.members", "lastClan.members", "battles"
                )
            }
        },
        {"$match": {"general_battles": {"$gte": 10}}},
        {
            "$addFields": {
                "general_wins": {
                    "$round": [
                        {
                            "$divide": [
                                member_stat_delta(
                                    "firstClan.members", "lastClan.members", "wins"
                                ),
                                "$general_battles",
                            ]
                        },
                        2,
                    ]
                },
                "general_damage": {
                    "$round": [
                        member_stat_delta(
                            "firstClan.members", "lastClan.members", "damage_dealt"
                        ),
                        2,
                    ]
                },
            }
        },
        {
            "$addFields": {
                "averageDamage": {
                    "$round": [{"$divide": ["$general_damage", "$general_battles"]}, 2]
                }
            }
        },
        {
            "$facet": {
                "stats": [
                    {
                        "$group": {
                            "_id": None,
                            "maxBattles": {"$max": "$general_battles"},
                            "minBattles": {"$min": "$general_battles"},
                            "maxWins": {"$max": "$general_wins"},
                            "minWins": {"$min": "$general_wins"},
                            "maxDamage": {"$max": "$averageDamage"},
                            "minDamage": {"$min": "$averageDamage"},
                        }
                    }
                ],
                "data": [
                    {
                        "$project": {
                            "_id": 0,
                            "name": 1,
                            "region": 1,
                            "tag": 1,
                            "clan_id": 1,
                            "general_battles": 1,
                            "general_wins": 1,
                            "averageDamage": 1,
                        }
                    }
                ],
            }
        },
        {"$project": {"stats": {"$arrayElemAt": ["$stats", 0]}, "data": "$data"}},
        {"$unwind": "$data"},
        {"$replaceRoot": {"newRoot": {"$mergeObjects": ["$data", "$stats"]}}},
        {
            "$addFields": {
                "x_w": {
                    "$divide": [
                        {"$subtract": ["$general_wins", "$minWins"]},
                        {"$subtract": ["$maxWins", "$minWins"]},
                    ]
                },
                "x_b": {
                    "$divide": [
                        {"$subtract": ["$general_battles", "$minBattles"]},
                        {"$subtract": ["$maxBattles", "$minBattles"]},
                    ]
                },
                "x_d": {
                    "$divide": [
                        {"$subtract": ["$averageDamage", "$minDamage"]},
                        {"$subtract": ["$maxDamage", "$minDamage"]},
                    ]
                },
            }
        },
        {
            "$addFields": {
                "rating": {
                    "$sum": [
                        {"$multiply": ["$x_d", 0.4]},
                        {"$multiply": ["$x_w", 0.3]},
                        {"$multiply": ["$x_b", 0.3]},
                    ]
                }
            }
        },
        {"$sort": {"rating": -1}},
    ]
