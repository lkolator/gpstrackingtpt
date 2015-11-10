function phoneValidator(phone) {
    var phoneRegex = /^\+([0-9]{10,11})$/;

    if (phone.match(phoneRegex)) {
        return true;
    } else {
        return false;
    }
}

function handleAct(cb) {
    var inputName;

    switch (cb.name) {
        case "htrAct":
            inputName = "#htrDiv";
            break;
        case "strAct":
            inputName = "#strDiv";
            break;
        case "tprAct":
            inputName = "#tprDiv";
            break;
        default:
    }

    if (cb.checked) {
        $(inputName + " :input").attr("disabled", false);
    } else {
        $(inputName + " :input").attr("disabled", true);
    }
}

function showAlert(container, message, type) {
    $(container).append('<div id="alertdiv" class="alert ' +  type +
                        '"><a class="close" data-dismiss="alert">×</a><span>'+
                        message+'</span></div>')
    setTimeout(function() {
        $("#alertdiv").remove();
    }, 5000);
}
