function send_order() {
    
    // TODO: check if list of analyses is filled.
    // TODO: do verification at server site!
    // order is name of form, so `<form name='order' ... >`
    const form = document.forms.match_list;
    form.action = "/o/accept"
    form.submit()
    console.log('submitted for save order to processing')
}
function add_games() {
    const form = document.forms.match_list;
    form.action = "/o/games";
    form.submit()
    console.log('submitted for adding games to order')
}

function modal_with_analyses() {
    
}