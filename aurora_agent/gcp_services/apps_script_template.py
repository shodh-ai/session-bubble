# in aurora_agent/gcp_services/apps_script_template.py

# This is the JavaScript code for our "spy" script.
# It uses a placeholder {{WEBHOOK_URL}} that our deployment service will replace.

APPS_SCRIPT_CODE = """
function onSpreadsheetChange(e) {
  // e is the event object from Google Sheets containing change details.
  
  // We only care about certain types of changes for the imprinter.
  // INSERT_GRID = New Sheet
  // EDIT = Cell value change
  // REMOVE_GRID = Delete Sheet
  // You can add more types like 'INSERT_ROW', 'REMOVE_ROW', etc.
  var relevantChangeTypes = ['INSERT_GRID', 'EDIT', 'REMOVE_GRID'];
  
  if (relevantChangeTypes.indexOf(e.changeType) === -1) {
    // If the change type isn't one we care about, do nothing.
    return;
  }

  // Prepare the data payload to send to our backend.
  var payload = {
    changeType: e.changeType,
    user: e.user ? e.user.email : 'unknown_user',
    timestamp: new Date().toISOString(),
    spreadsheetId: e.source ? e.source.getId() : 'unknown_spreadsheet',
    sheetName: e.source ? e.source.getActiveSheet().getName() : 'unknown_sheet',
    range: e.range ? e.range.getA1Notation() : 'unknown_range'
    // We can add more context from 'e' later if needed,
    // like the range that was edited.
  };

  // Define the options for the webhook POST request.
  var options = {
    method: 'post',
    contentType: 'application/json',
    // Mute exceptions so that if our server is down,
    // it doesn't show an error to the teacher in Google Sheets.
    muteHttpExceptions: true,
    payload: JSON.stringify(payload)
  };

  // Send the data to our backend's webhook listener.
  try {
    UrlFetchApp.fetch("{{WEBHOOK_URL}}", options);
  } catch (error) {
    // Silent fail - don't interrupt the user's workflow
    console.log('Aurora Agent webhook failed:', error);
  }
}

function onInstall(e) {
  // This function runs when the script is first installed
  // We can use it to set up initial configurations if needed
  console.log('Aurora Agent spy script installed successfully');
}
"""
