function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}


$(function () {
    $(".pass_info").submit(function (e) {
        e.preventDefault();

        // 修改密码
        var params = {}
        $(this).serializeArray().map(function(x){
            params[x.name] = x.value
        })
        // 取到两次密码
        var new_password = params['new_password']
        var new_password2 = params['new_password2']
        if (new_password != new_password2){
            alert('两次密码不一致')
            return
        }
        $.ajax({
            url:"/user/pass_info",
            type:"post",
            contentType:"application/json",
            data:JSON.stringify(params),
            headers:{
                'X-CSRFToken':getCookie('csrf_token')
            },
            success:function(resp){
                if (resp.error == "0"){
                    alert('修改成功')
                    window.location.reload()
                }else{
                    alert(resp.errmsg)
                }
            }
        })

    })
})