// Fetch and save the COMPLETE notification history (no truncation)
// Table ID is read from the current URL automatically
(function() {
    var tableMatch = window.location.search.match(/table=(\d+)/);
    if (!tableMatch) return JSON.stringify({error: 'No table= param in URL'});
    var tableId = parseInt(tableMatch[1]);
    var pathParts = window.location.pathname.split('/');
    // URL can be /<N>/innovation or /<N>/innovation/innovation — handle both
    var gameName = pathParts[3] || pathParts[2];
    var endpoint = '/' + pathParts[1] + '/' + pathParts[2] + '/' + gameName + '/notificationHistory.html';
    return new Promise(function(resolve) {
        gameui.ajaxcall(
            endpoint,
            {table: tableId, from: 0, privateinc: 1, history: 1},
            gameui,
            function(result) {
                // Store full result in a global so we can access it
                window.__full_history = result;
                var json = JSON.stringify(result);
                // Return size info + first chunk
                resolve(JSON.stringify({
                    total_chars: json.length,
                    data_entries: Array.isArray(result) ? result.length : 'not array',
                    type: typeof result,
                    keys: result && typeof result === 'object' && !Array.isArray(result) ? Object.keys(result) : 'N/A'
                }));
            },
            function(is_error, error_msg) {
                resolve(JSON.stringify({error: true, msg: error_msg}));
            }
        );
    });
})();
