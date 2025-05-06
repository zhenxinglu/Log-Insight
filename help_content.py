# Help content for Log Insight application


def get_help_content() -> str:
    """
    Returns the help content for the Log Insight application
    
    Returns:
        str: HTML formatted help content
    """
    return """
    <h2>Log Insight Features</h2>
    <p>Log Insight is a powerful log file viewing and analysis tool that provides the following features:</p>
    
    <h3>Main Features</h3>
    <ul>
        <li><b>Log Filtering</b> - Filter log content based on keywords and time range</li>
        <li><b>Real-time Monitoring</b> - Monitor log file changes in real-time</li>
        <li><b>Text Search</b> - Search for specific text within log content</li>
        <li><b>Theme Switching</b> - Support for light and dark themes</li>
        <li><b>Word Wrap</b> - Control whether text automatically wraps</li>
    </ul>
    
    <h3>Keyboard Shortcuts</h3>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr>
            <th>Shortcut</th>
            <th>Function</th>
        </tr>
        <tr>
            <td>Ctrl+F</td>
            <td>Search for text in log content</td>
        </tr>
        <tr>
            <td>F1</td>
            <td>Display help dialog</td>
        </tr>
        <tr>
            <td>Ctrl+Mouse Wheel</td>
            <td>Adjust font size</td>
        </tr>
        <tr>
            <td>Enter (in filter input fields)</td>
            <td>Apply filter conditions</td>
        </tr>
    </table>
    
    <h3>Filter Function Description</h3>
    <p><b>Include Keywords</b> - Only display log lines containing specified keywords</p>
    <p><b>Exclude Keywords</b> - Do not display log lines containing specified keywords</p>
    <p><b>Time Range</b> - Only display log lines within the specified time range (Format: HH:MM:SS.mmm)</p>
    <p>Keywords support the following formats:</p>
    <ul>
        <li>Single keyword: <code>error</code></li>
        <li>Multiple keywords (space-separated): <code>error warning</code></li>
        <li>Keywords containing spaces (use quotes): <code>"connection failed"</code></li>
    </ul>
    
    <h3>Other Features</h3>
    <p><b>Drag and Drop Support</b> - Open log files by dragging and dropping them into the application window</p>
    <p><b>Auto-save Settings</b> - Automatically save filter conditions, theme settings, and other configurations</p>
    """