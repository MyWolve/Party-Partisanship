"""Generate descriptive E1 narrative from its audited, in-memory tables."""
PRIME_MINISTER = {'38-1': 'Martin', **{s: 'Harper' for s in
    ('39-1', '39-2', '40-1', '40-2', '40-3', '41-1', '41-2')},
    **{s: 'Trudeau' for s in ('42-1', '43-1', '43-2', '44-1')}, '45-1': 'Carney'}
INCOMPLETE_SESSIONS = {'45-1'}
SMALL_N = 30
BILL_NOTES = {
    ('38-1', 'C-38'): 'The recommittal stage is unresolved; documented substantive free stages are excluded.',
    ('38-1', 'C-30'): 'Pay legislation; the audit does not establish Liberal whip instructions.',
    ('38-1', 'C-17'): 'Committee referral; the audit does not establish whip instructions.',
    ('42-1', 'C-14'): 'Senate-amendment scope remains unresolved; documented substantive free stages are excluded.',
    ('42-1', 'C-89'): 'The division subjects concern resumption and continuation of postal services.',
    ('43-2', 'C-7'): 'The division subjects concern Senate amendments on medical assistance in dying.',
}


def eligible(row):
    return (row['governing'] and row['category'] == 'government_bill'
            and row['majority_defined'] and row['whip_status'] != 'documented_free')


def chronology(row, sessions):
    return sessions.index(row['session']), int(row['division'])


def longest_clean_run(classifications, sessions):
    """Longest zero-dissent sequence in eligible divisions, not all House votes.

    Ineligible observations neither add to nor interrupt a caucus's run.
    A governing-party transition is a boundary even if its first vote is ineligible.
    Equal-length runs retain the earliest one.
    """
    best, current, party = [], [], None
    for r in sorted((r for r in classifications if r['governing']), key=lambda r: chronology(r, sessions)):
        if r['party'] != party:
            current, party = [], r['party']
        if not eligible(r):
            continue
        if r['dissenters']:
            current = []
        else:
            current.append(r)
            if len(current) > len(best):
                best = current.copy()
    return best


def percent(n, d):
    return 100 * n / d if d else None


def cell(value):
    n, d = value
    return f'{n}/{d} ({percent(n, d):.2f}%)' if d else 'No eligible divisions'


def narrative_lines(rows, classifications, government, sessions):
    selected = [r for r in rows if r['scope'] == 'documented_free_excluded'
                and r['variant'] == 'all' and r['party'] == government[r['session']]]
    cells = {(r['session'], r['category']): (r['with_dissent'], r['divisions']) for r in selected}
    def get(session, category):
        return cells.get((session, category), (0, 0))
    def pool(wanted, category):
        pairs = [get(s, category) for s in wanted]
        return sum(n for n, d in pairs), sum(d for n, d in pairs)

    lines = ['## What stands out', '']
    run = longest_clean_run(classifications, sessions)
    if run:
        start, end = run[0], run[-1]
        spanned = sessions[sessions.index(start['session']):sessions.index(end['session'])+1]
        rates = [percent(*get(s, 'private_members_business')) for s in spanned
                 if government[s] == start['party'] and get(s, 'private_members_business')[1]]
        dates = f" ({start['date'][:10]} to {end['date'][:10]})" if start.get('date') and end.get('date') else ''
        text = (f"- **Longest zero-dissent run:** {len(run)} consecutive eligible {start['party']} government-bill divisions, "
                f"from {start['session']}/{start['division']} to {end['session']}/{end['division']}{dates}. "
                f"Sessions spanned: {', '.join(spanned)}.")
        if rates:
            text += f" The same caucus's session rates on private business range from {min(rates):.2f}% to {max(rates):.2f}% in that span."
        if '40-1' in spanned and not get('40-1', 'government_bill')[1]:
            text += ' The span crosses omitted session 40-1, whose single Throne Speech division contributes no government-bill observations.'
        lines.append(text + ' Consecutive means within the eligible series; this is not a claim about every House vote or verified whip instructions.')

    harper = pool([s for s in sessions if PRIME_MINISTER[s] == 'Harper'], 'government_bill')
    later = pool([s for s in sessions if PRIME_MINISTER[s] in ('Trudeau', 'Carney')], 'government_bill')
    if harper[1] and later[1]:
        ratio = percent(*later) / percent(*harper) if harper[0] else None
        extra = f' The later rate is {ratio:.2f} times the earlier rate.' if ratio is not None else ' The rate ratio is undefined.'
        lines.append(f'- **Governing-party comparison:** Harper-era Conservative government bills: {cell(harper)}; '
            f'Trudeau/Carney-era Liberal government bills: {cell(later)}.' + extra +
            ' This pools different sessions and business mixes; it does not identify an effect of leadership or whip policy. Martin is shown separately below.')

    qualified = [s for s in sessions if get(s, 'government_bill')[1] >= SMALL_N]
    if qualified:
        loosest = max(qualified, key=lambda s: percent(*get(s, 'government_bill')))
        text = f'- **Highest government-bill dissent rate:** {loosest} ({PRIME_MINISTER[loosest]}, {government[loosest]}), {cell(get(loosest, "government_bill"))}, among sessions with at least {SMALL_N} eligible government-bill divisions.'
        private = [s for s in sessions if get(s, 'private_members_business')[1] >= SMALL_N]
        if private and loosest == max(private, key=lambda s: percent(*get(s, 'private_members_business'))):
            text += f" It also has the highest private-business rate among sessions meeting that category's {SMALL_N}-division threshold: {cell(get(loosest, 'private_members_business'))}."
        lines.append(text)
    lines.append(f"- **Supply:** {cell(pool(sessions, 'supply'))} eligible divisions contain governing-party dissent.")
    for s in sessions:
        g, p = get(s, 'government_bill'), get(s, 'private_members_business')
        if g[0] and p[1] and percent(*p)/percent(*g) < 1.5:
            lines.append(f'- **Narrow category gap:** {s}: government bills {cell(g)}, private business {cell(p)}, '
                f'ratio {percent(*p)/percent(*g):.2f}.' + (' This session is incomplete.' if s in INCOMPLETE_SESSIONS else '') +
                ' E2 remains needed to examine changes over time; this contrast alone does not establish a trend.')

    lines += ['', '## By session (governing party)', '',
        '| Session | Leader and party | Government bills | Private business | Notes |', '| --- | --- | --- | --- | --- |']
    for s in sessions:
        if s == '40-1':
            continue
        g, p = get(s, 'government_bill'), get(s, 'private_members_business')
        notes = []
        free = sum(r['session'] == s and r['governing'] and r['whip_status'] == 'documented_free' for r in classifications)
        if free:
            notes.append(f'{free} documented free divisions excluded')
        if not p[1]:
            notes.append('No eligible private-business divisions')
        if g[1] < SMALL_N or 0 < p[1] < SMALL_N:
            notes.append(f'Small denominator (<{SMALL_N})')
        if s in INCOMPLETE_SESSIONS:
            notes.append('Incomplete snapshot')
        lines.append(f"| {s} | {PRIME_MINISTER[s]} / {government[s]} | {cell(g)} | {cell(p)} | {'; '.join(notes)} |")
    lines += ['', 'Cells count divisions with dissent / eligible divisions. Session 40-1 is omitted for its single Throne Speech division. Leader names label sessions; calculations use the governing party.', '',
        '## Largest governing-party dissent episodes on government bills', '',
        '| Session/division | Bill | Stage | Dissenters | Status |', '| --- | --- | --- | --- | --- |']
    ranked = sorted((r for r in classifications if eligible(r) and r['dissenters']),
                    key=lambda r: (-r['dissenters'], *chronology(r, sessions)))
    shown = ranked[:12]
    for r in shown:
        status = 'unresolved' if r['whip_status'] == 'unresolved' else 'category proxy'
        lines.append(f"| {r['session']}/{r['division']} | {r['bill'] or 'Unknown'} | {r['stage'] or 'Unclassified'} | {r['dissenters']} | {status} |")
    lines += ['', 'These are observed dissent episodes, not confirmed breaches of whip instructions. Documented free stages are excluded; unresolved stages remain visible.', '']
    for key in dict.fromkeys((r['session'], r['bill']) for r in shown):
        if key in BILL_NOTES:
            lines.append(f'- {key[0]} {key[1]}: {BILL_NOTES[key]}')
    candidate = next((r for r in ranked if r['whip_status'] != 'unresolved'), None)
    if candidate:
        lines += ['', f"The largest episode not already flagged unresolved is **{candidate['bill']}, "
            f"{candidate['session']}/{candidate['division']}, with {candidate['dissenters']} dissenters**. "
            'By dissent count, it is the leading candidate for further investigation of a rebellion on whipped business. '
            'Its category-proxy status is not evidence of a whip instruction; that instruction still needs a source.']
    return lines + ['']
