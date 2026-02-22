// Extract game log v5 - player & spectator notifs are in separate packets per move
(function() {
    var history = window.__full_history;
    if (!history || !history.data) return JSON.stringify({error: 'No history data.'});

    var packets = history.data;
    var log = [];

    var iconMap = {'1': 'crown', '2': 'leaf', '3': 'lightbulb', '4': 'castle', '5': 'factory', '6': 'clock'};

    var playerNames = {};
    if (typeof gameui !== 'undefined' && gameui.gamedatas && gameui.gamedatas.players) {
        var players = gameui.gamedatas.players;
        for (var pid in players) { playerNames[pid] = players[pid].name; }
    }

    function expandTemplate(template, args) {
        if (!template) return '';
        return template.replace(/\$\{([^}]+)\}/g, function(match, key) {
            var val = args[key];
            if (val === undefined || val === null) return '';
            if (typeof val === 'object' && !Array.isArray(val)) {
                if (val.log && val.args) {
                    return expandTemplate(val.log, val.args).replace(/<[^>]+>/g, '').trim();
                }
                if (val.name) return val.name;
                return '';
            }
            return String(val);
        });
    }

    function cleanHtml(msg) {
        msg = msg.replace(/<span[^>]*icon_(\d)[^>]*><\/span>/g, function(m, num) {
            return '[' + (iconMap[num] || 'icon' + num) + ']';
        });
        msg = msg.replace(/<span[^>]*age[^>]*>(\d+)<\/span>/g, '[$1]');
        msg = msg.replace(/<[^>]+>/g, '');
        return msg.replace(/\s+/g, ' ').trim();
    }

    // Pass 1: collect all player transferedCard notifications grouped by move_id (in order)
    var playerTransfersByMove = {};
    for (var p = 0; p < packets.length; p++) {
        var notifs = packets[p].data || [];
        var move_id = packets[p].move_id;
        for (var n = 0; n < notifs.length; n++) {
            if (notifs[n].type === 'transferedCard' && notifs[n].args) {
                if (!playerTransfersByMove[move_id]) playerTransfersByMove[move_id] = [];
                playerTransfersByMove[move_id].push(notifs[n].args);
            }
        }
    }

    // Also collect player log and logWithCardTooltips per move
    var playerLogsByMove = {};
    for (var p = 0; p < packets.length; p++) {
        var notifs = packets[p].data || [];
        var move_id = packets[p].move_id;
        for (var n = 0; n < notifs.length; n++) {
            var type = notifs[n].type;
            if ((type === 'log' || type === 'logWithCardTooltips') && notifs[n].args) {
                if (!playerLogsByMove[move_id]) playerLogsByMove[move_id] = [];
                playerLogsByMove[move_id].push(notifs[n]);
            }
        }
    }

    // Pass 2: process spectator notifications, enriching transfers with player data
    var transferCountByMove = {};

    for (var p = 0; p < packets.length; p++) {
        var packet = packets[p];
        var move_id = packet.move_id;
        var time = packet.time;
        var notifs = packet.data || [];

        for (var n = 0; n < notifs.length; n++) {
            var notif = notifs[n];
            var type = notif.type;
            var args = notif.args || {};

            // Only process spectator notifications
            if (type === 'transferedCard_spectator') {
                if (!transferCountByMove[move_id]) transferCountByMove[move_id] = 0;
                var idx = transferCountByMove[move_id]++;
                var playerArgs = (playerTransfersByMove[move_id] || [])[idx];

                if (playerArgs && playerArgs.name) {
                    // Build rich message from player data
                    var player = playerNames[playerArgs.player_id] || playerNames[playerArgs.owner_from] || playerArgs.player_id;
                    var card = '[' + playerArgs.age + '] ' + playerArgs.name;
                    var from = playerArgs.location_from;
                    var to = playerArgs.location_to;
                    var ownerFrom = playerArgs.owner_from;
                    var ownerTo = playerArgs.owner_to;
                    var opponent = playerNames[playerArgs.opponent_id] || '';
                    if (!opponent && ownerTo && ownerTo !== ownerFrom && ownerTo !== '0') opponent = playerNames[ownerTo] || ownerTo;
                    if (!opponent && ownerFrom && ownerFrom !== ownerTo && ownerFrom !== '0') opponent = playerNames[ownerFrom] || ownerFrom;

                    var msg;
                    if (from === 'hand' && to === 'board' && ownerFrom === ownerTo) {
                        msg = player + (playerArgs.bottom_to ? ' tucks ' : ' melds ') + card + ' from hand.';
                    } else if (from === 'deck' && to === 'hand') {
                        msg = player + ' draws ' + card + '.';
                    } else if (from === 'deck' && to === 'revealed') {
                        msg = player + ' draws and reveals ' + card + '.';
                    } else if (from === 'deck' && to === 'score') {
                        msg = player + ' draws and scores ' + card + '.';
                    } else if (from === 'deck' && to === 'board') {
                        msg = player + ' draws and melds ' + card + '.';
                    } else if (from === 'revealed' && to === 'hand') {
                        msg = player + ' places ' + card + ' in hand.';
                    } else if (from === 'revealed' && to === 'deck') {
                        msg = player + ' returns revealed ' + card + '.';
                    } else if (from === 'hand' && to === 'score' && ownerFrom === ownerTo) {
                        msg = player + ' scores ' + card + ' from hand.';
                    } else if (from === 'hand' && to === 'hand' && ownerFrom !== ownerTo) {
                        msg = (playerNames[ownerFrom] || player) + ' transfers ' + card + ' from hand to ' + (playerNames[ownerTo] || opponent) + "'s hand.";
                    } else if (from === 'hand' && to === 'score' && ownerFrom !== ownerTo) {
                        msg = (playerNames[ownerFrom] || player) + ' transfers ' + card + ' from hand to ' + (playerNames[ownerTo] || opponent) + "'s score pile.";
                    } else if (from === 'score' && to === 'hand' && ownerFrom === ownerTo) {
                        msg = player + ' moves ' + card + ' from score pile to hand.';
                    } else if (from === 'hand' && to === 'deck') {
                        msg = player + ' returns ' + card + ' from hand.';
                    } else if (from === 'score' && to === 'deck') {
                        msg = player + ' returns ' + card + ' from score pile.';
                    } else if (to === 'achievements' || to === 'claimed') {
                        msg = player + ' achieves ' + card + '.';
                    } else if (from === 'board' && to === 'hand') {
                        msg = player + ' returns ' + card + ' from board to hand.';
                    } else if (from === 'board' && to === 'score') {
                        msg = player + ' scores ' + card + ' from board.';
                    } else if (from === 'board' && to === 'deck') {
                        msg = player + ' returns ' + card + ' from board.';
                    } else if (from === 'revealed' && to === 'board') {
                        msg = player + ' melds ' + card + '.';
                    } else {
                        msg = player + ' moves ' + card + ' (' + from + ' -> ' + to + ').';
                    }

                    log.push({move: parseInt(move_id), time: parseInt(time), type: 'transfer', msg: msg});
                } else {
                    // Fallback to spectator template (hidden card)
                    var logTemplate = args.log || '';
                    if (!logTemplate) continue;
                    var logMsg = cleanHtml(expandTemplate(logTemplate, args));
                    if (logMsg) {
                        // Append set info: BGA type 0 = base, type 2 = cities
                        var setName = args.type === '2' ? 'cities' : 'base';
                        logMsg = logMsg.replace(/\.$/, ' from ' + setName + '.');
                        log.push({move: parseInt(move_id), time: parseInt(time), type: 'transfer', msg: logMsg});
                    }
                }
                continue;
            }

            if (type === 'log_spectator' || type === 'logWithCardTooltips_spectator') {
                var logTemplate = args.log || notif.log || '';
                if (!logTemplate || logTemplate === '<!--empty-->') continue;
                var logMsg = cleanHtml(expandTemplate(logTemplate, args));
                if (logMsg) {
                    log.push({
                        move: parseInt(move_id),
                        time: parseInt(time),
                        type: type.replace('_spectator', ''),
                        msg: logMsg
                    });
                }
            }
        }
    }

    return JSON.stringify({total_entries: log.length, log: log}, null, 2);
})();
