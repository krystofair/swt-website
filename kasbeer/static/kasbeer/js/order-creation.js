function send_order() {
    
    // TODO: check if list of analyses is filled.
    // TODO: do verification at server site!
    // order is name of form, so `<form name='order' ... >`
    const form = document.forms.match_list;
    form.action = "/o/accept"
    let os_input = document.getElementById('order_summary')
    let input_hidden_os = os_input.cloneNode()
    input_hidden_os.type = 'hidden'
    form.append(input_hidden_os)
    form.submit()
    console.log('submitted for save order to processing')
}
function add_games() {
    const form = document.forms.match_list;
    form.action = "/o/games";
    form.submit()
    console.log('submitted for adding games to order')
}

function change_game_callback(event) {
    let self = event.target
    console.debug("Event change received from:" + self)
    let form_total_forms = document.getElementById('match_list_chosen_count')
    if (self.checked) {
        form_total_forms.value = parseInt(form_total_forms.value) + 1;
    } else {
        form_total_forms.value = parseInt(form_total_forms.value) - 1;
    }
}

function modal_with_analyses() {
    
}