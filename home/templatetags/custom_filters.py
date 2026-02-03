from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def get_item_team(dictionary, team_id):
    # This assumes a structure of {(team_id, player_id): stats}
    # To use in template: player_stats_map|get_match_stats:team.id|get_item:player.id
    # Actually, let's just make one filter that takes both if possible, or just build a nested dict in view.
    # Let's fix the view to provide a nested dict.
    return dictionary.get(team_id, {})
