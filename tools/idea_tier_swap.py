"""Render native spirit upgrades while keeping legacy stack cleanup out of tooltips."""


def hidden_cleanup(ideas):
    ideas = list(dict.fromkeys(ideas))
    if not ideas:
        return ''
    return 'hidden_effect = { ' + ' '.join('remove_ideas = ' + idea for idea in ideas) + ' }'


def tier_swap(target, candidates):
    candidates = [idea for idea in dict.fromkeys(candidates) if idea != target]
    branches = []
    for idea in reversed(candidates):
        keyword = 'if' if not branches else 'else_if'
        branches.append(keyword + ' = { limit = { has_idea = ' + idea + ' } '
                        'swap_ideas = { remove_idea = ' + idea + ' add_idea = ' + target + ' } }')
    branches.append(('else = { ' if branches else '') + 'add_ideas = ' + target
                    + (' }' if branches else ''))
    return ' '.join(branches) + ' ' + hidden_cleanup(candidates)
