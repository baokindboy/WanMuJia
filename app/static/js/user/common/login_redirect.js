function redirectLogin(){var t=$("#login"),r=window.location.pathname;return-1!==r.indexOf("login")?void t.attr("href",window.location.href):-1!==r.indexOf("register")?void t.attr("href",t.attr("href")+"?next=/"):void t.attr("href",t.attr("href")+"?next="+r)}$(function(){redirectLogin()});