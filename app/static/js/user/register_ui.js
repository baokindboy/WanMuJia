function btnLoading(e){e.attr("disabled",!0),e.val("Loading...")}function btnClearLoading(e,t){e.attr("disabled",!1),e.val(t)}function sendEnable(e,t){e.val(t),e.removeClass("disabled")}function sendDisable(e,t,n){var a=parseInt((n-t+parseInt(getCookie("clickTime")))/1e3);e.addClass("disabled"),e.val(a+" 秒后再次发送")}function setCountDown(e,t,n){var a=setInterval(function(){Date.now()-getCookie("clickTime")>=n-1e3?(clearTimeout(a),sendEnable(e,t),setCookie("clickTime","",new Date(0))):sendDisable(e,Date.now(),n)},200)}function isMobilePhone(e){var t=/^1\d{10}$/;return t.exec(e)?!0:!1}function isEmail(e){var t=/^([a-zA-Z0-9]+[_|\_|\.]?)*[a-zA-Z0-9]+@([a-zA-Z0-9]+[_|\_|\.]?)*[a-zA-Z0-9]+\.[a-zA-Z]{2,3}$/;return t.test(e)?!0:!1}$(function(){function e(){var e=c.val();return 0===e.length?(v.fadeIn("100").text("请输入手机号码"),!1):isMobilePhone(e)?(v.text(" ").fadeOut("50"),!0):(v.fadeIn("100").text("请输入正确的手机号码"),!1)}function t(){var e=l.val();return 0===e.length?(g.fadeIn("100").text("请输入验证码"),!1):(g.text(" ").fadeOut("50"),!0)}function n(){var e=u.val();return 0===e.length?(m.fadeIn("100").text("请输入邮箱"),!1):isEmail(e)?(m.text(" ").fadeOut("50"),!0):(m.fadeIn("100").text("请输入正确的邮箱地址"),!1)}function a(){var e=f.is(":checked");return e?(b.text(" ").fadeOut("50"),!0):(b.fadeIn("100").text("请选择同意万木家服务协议"),!1)}var i="/register_next",r="/service/mobile_register_sms",o="/register",s="/service/send_email?type=USER_REGISTER",c=$("#mp"),l=$("#verify"),u=$("#email"),f=$("#agreement"),d=$("#csrf_token"),v=$(".err-tip.mp"),g=$(".err-tip.ver"),m=$(".err-tip.email"),b=$(".err-tip.agreement"),h=($(".agreement"),$("#next")),x=$(".send"),k=$("#sendEmail"),p=6e4,w=x.val();getCookie("clickTime")&&(sendDisable(x,Date.now(),p),setCountDown(x,w,p)),$(".another-way").click(function(e){$this=$(this),$this.parents('[class|="way"]').hide(),$(".way-"+$this.data("way")).show(),e.preventDefault()}),c.blur(function(){e()}),x.click(function(){if(e()){var t=$(this);t.hasClass("disabled")||$.ajax({type:"POST",url:r,data:{mobile:c.val()},success:function(e){e.success?(setCookie("clickTime",Date.now()),setCountDown(t,w,p)):v.fadeIn("100").text(e.message)},error:function(e,t,n){console.error(r,t,n.toString())}})}}),l.blur(function(){t()}),f.change(function(){var e=f.is(":checked");e&&b.text(" ").fadeOut("50")}),h.click(function(n){if(n.preventDefault(),!e())return!1;if(!t())return!1;if(!a())return!1;var r=$(this),s=r.val();btnLoading(r),$.ajax({type:"POST",url:o,data:{mobile:c.val(),captcha:l.val(),csrf_token:d.val()},success:function(e){btnClearLoading(r,s),e.success?window.location.href=i:v.fadeIn("100").text(e.message)},error:function(e,t,n){console.error(o,t,n.toString())}})}),u.blur(function(){n()}),k.click(function(e){if(e.preventDefault(),n()){var t=$(this),a=t.val();btnLoading(t),$.ajax({type:"POST",url:s,data:{email:u.val(),csrf_token:d.val()},success:function(e){btnClearLoading(t,a),m.fadeIn("100").text(e.success?"邮件发送成功":e.message)},error:function(e,t,n){console.error(s,t,n.toString())}})}})});