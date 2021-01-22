import json
from collections import defaultdict

from bots import defmt_bot_name
from leaguesettings import LeagueSettings
from match import MatchDetails
from match_maker import TicketSystem
from paths import LeagueDir, PackageFiles
from ranking_system import RankingSystem


def make_summary(ld: LeagueDir, count: int):
    """
    Make a summary of the N latest matches and the resulting ranks and tickets.
    If N is 0 the summary will just contain the current ratings.
    """
    summary = {}

    tickets = TicketSystem.load(ld)

    # ========== Matches ==========

    matches = []
    bot_wins = defaultdict(list)   # Maps bots to list of booleans, where true=win and false=loss

    if count > 0:
        latest_matches = MatchDetails.latest(ld, count)
        for i, match in enumerate(latest_matches):
            matches.append({
                "index": i,
                "blue_names": [defmt_bot_name(bot_id) for bot_id in match.blue],
                "orange_names": [defmt_bot_name(bot_id) for bot_id in match.orange],
                "blue_goals": match.result.blue_goals,
                "orange_goals": match.result.orange_goals,
            })
            for bot in match.blue:
                bot_wins[bot].append(match.result.blue_goals > match.result.orange_goals)
            for bot in match.orange:
                bot_wins[bot].append(match.result.blue_goals < match.result.orange_goals)

    summary["matches"] = matches

    # ========= Ranks/Ratings =========

    bots_by_rank = []

    if count <= 0:
        # When count == 0 we just show the current rankings
        cur_rankings = RankingSystem.latest(ld, 1)[0].as_sorted_list()
        for i, (bot, mrr, sigma) in enumerate(cur_rankings):
            cur_rank = i + 1
            bots_by_rank.append({
                "bot_id": defmt_bot_name(bot),
                "mmr": mrr,
                "sigma": sigma,
                "cur_rank": cur_rank,
                "old_rank": cur_rank,
                "tickets": tickets.get(bot),
                "wins": [],
            })

    else:
        # Determine current rank and their to N matches ago
        n_rankings = RankingSystem.latest(ld, count)
        old_rankings = n_rankings[0].as_sorted_list()
        cur_rankings = n_rankings[-1].as_sorted_list()

        for i, (bot, mrr, sigma) in enumerate(cur_rankings):
            cur_rank = i + 1
            old_rank = None
            old_mmr = None
            for j, (other_bot, other_mrr, _) in enumerate(old_rankings):
                if bot == other_bot:
                    old_rank = j + 1
                    old_mmr = other_mrr
                    break
            bots_by_rank.append({
                "bot_id": defmt_bot_name(bot),
                "mmr": mrr,
                "old_mmr": old_mmr,
                "sigma": sigma,
                "cur_rank": cur_rank,
                "old_rank": old_rank,
                "tickets": tickets.get(bot),
                "wins": bot_wins[bot],
            })

    summary["bots_by_rank"] = bots_by_rank

    # =========== Write =============

    with open(PackageFiles.overlay_summary, 'w') as f:
        json.dump(summary, f, indent=4)

    league_settings = LeagueSettings.load(ld)
    league_settings.last_summary = count
    league_settings.save(ld)
