<img src="./static/banner.png" width="100%">

## Description

<img src="./static/screenshot.png">


Stock Trading App that allows you to look up stocks, buy, sell, and logs your transaction history.  Additional features include sign in, authentication, deposit, change passwords. Created as part of the CS50 webapp project.

### Technologies Used: 

- Python
- Javascript
- IEX API
- SQL 
- Flask
- JQuery
- Bootstrap4


### Configuring
Before getting started, you'll need to register for an API key in order to be able to query IEX’s data. To do so, follow these steps:

- Visit iexcloud.io/cloud-login#/register/.
-	Enter your email address and a password, and click “Create account”.
- On the next page, scroll down to choose the Start (free) plan.
- Once you’ve confirmed your account via a confirmation email, sign in to iexcloud.io.
- Click API Tokens.
- Copy the key that appears under the Token column (it should begin with pk_).
In a terminal window execute:
```
$ export API_KEY=value
```
where value is that (pasted) value, without any space immediately before or after the =. 

### Quickstart
```
cd finance
flask run 
```
