# Set up OAuth 2.0

## Note about deprecation of TLS1.0 and TLS1.1

As we mentioned in our previous blog posts, we're no longer supporting TLS1.0 and TLS1.1 starting June 1st, 2022. We'll only support TLS1.2 or higher going forward. Refer to our blog for more details:

- [TLS 1.0 and 1.1 Disablement for the Intuit Developer Group](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- [Upgrading your apps to support TLS 1.2](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)

## Set up OAuth 2.0

Use the [OAuth 2.0 protocol](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0) to implement authentication and authorization. Authorization is essential for both testing via sandbox companies and production apps.

We'll show you how to set up the authorization flow so users can authorize to your app and give it permission to connect to their QuickBooks Online company.

If users grant permission, our Intuit OAuth 2.0 Server sends an authorization code back to your app. Your app exchanges this code for access tokens. These tokens are tied to your users' now authorized QuickBooks Online company (identified by the **realmID**).

Your app needs access tokens to [make API calls](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0) and interact with QuickBooks Online data.

## Step 1: Create your app on the Intuit Developer Portal

Start by [signing in](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0) to your developer account and [creating an app on the Intuit Developer Portal](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0).

When you create your app, select the [QuickBooks Online Accounting scope](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0).

This app provides the credentials you'll need for authorization requests.

## Step 2: Practice authorization in the OAuth Playground

Check out the [OAuth Playground](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0) to preview each step of the authorization flow. We've provided sample data, like the redirect URI, so you can focus on the overall flow.

Using the OAuth Playground isn't required, but we recommend it.

## Step 3: Start developing with an SDK

Our SDKs come with a built-in OAuth 2.0 Client Library and handle many parts of the authorization implementation for you. For instance, our SDKs implement handlers that automatically exchange the authorization codes sent from the Intuit OAuth 2.0 Server for access tokens.

Select a link to download an SDK:

- [OAuth 2.0 Client Library for .Net](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- [OAuth 2.0 Client Library for Java](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- [OAuth 2.0 Client Library for PHP](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- [OAuth 2.0 Client Library for Node.js](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- [OAuth 2.0 Client Library for Python](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- [OAuth 2.0 Client Library for Ruby](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)

### .NET
```
Install-Package IppDotNetSdkForQuickBooksApiV3
```

### Java
```
Download the latest version of oauth2-platform-api.jar and include it in your project.
Sample below shows how to add it to a gradle project:
compile (group: 'com.intuit.quickbooks-online', name: 'oauth2-platform-api', version: '6.0.7', classifier: 'jar-with-dependencies')
```

### PHP
```
composer require quickbooks/v3-php-sdk
```

### Node.js
```
npm install intuit-oauth
```

### Python
```
pip install intuit-oauth
```

### Ruby
```
gem install 'intuit-oauth'
```

## Step 4: Understand the end-to-end authorization flow

While authorization is a simple step for app users, it involves several tasks on the backend. Here's an brief overview:

### Creating authorization requests

- Review the scopes you selected for your app. These determine what data and API it can access. You may want to use the `openID` scope to implement OpenID Connect in addition to others.
- Configure your app so it uses the correct credentials (i.e. Client ID and Client secret) and redirect URIs.
- Review the base URLs in our authorization discovery documents.
- Use this info to create authorization requests.

### Managing the authorization flow

- When a user connects to your app, it sends an authorization request to the Intuit OAuth 2.0 Server.
- The user gets redirected to an authorization page where they can give your app permission to access their QuickBooks Online company and its data. This is the "user consent" step of the process.
- If the user authorizes your app, the Intuit OAuth 2.0 Server sends an authorization code back to your app.

### Getting access and refresh tokens

- Your app sends the authorization code back to the Intuit OAuth 2.0 Server and exchanges it for access and refresh tokens.
- Your app extracts the latest access and refresh tokens from the server response.

### Making API calls

- Use access tokens to call specific APIs and interact with users' QuickBooks Online company data.
- When access tokens expire, use a refresh token to "refresh" the access token.
- If a refresh token expires, users need to go through the authorization flow again.

## Step 5: Get your app's credentials

Sign in to your Intuit Developer account and get your app's Client ID and Client secret.

If you're implementing authorization for a live, in-production app, go to the **Production** section and select **Keys & OAuth** to get your credentials.

If you're implementing authorization for testing with a sandbox company, go to the **Development** section and select **Keys & OAuth** to get your credentials.

## Step 6: Learn about discovery documents

OAuth 2.0 requires multiple URLs for authentication and requests for resources like tokens, user info, and credentials.

Use our discovery documents to simplify the implementation. These JSON documents, found at a well known location, contain field : value pairs and URL endpoints for `authorization`, `token`, `userinfo`, and other data points.

## Step 7: Add your app's redirect URIs

Redirect URIs handle responses from the Intuit OAuth 2.0 Server during the authorization flow. Basically, they're your app's endpoints.

Add at least one redirect URI for your app.

If you're developing with an SDK, use the URI value generated by the SDK.

## Step 8: Create an authorization request

Create the authorization request your app will send to the Intuit OAuth 2.0 Server when users connect to your app.

Request parameters should identify your app and include the required scopes.

### Required parameters

**client_id**: The `client_id` of your app.

**scope**: Lists the scopes your app uses.

Enter one or more scopes. The list should be space-delimited. The `scope` value defines the type of data an app can utilize. This information appears on the authorization page users see when they connect to your app.

**Tip**: We recommend apps request scopes incrementally based on your feature requirements, rather than all scopes up front.

**redirect_uri**: The redirect URI for your app.

**response_type**: States if the Intuit OAuth 2.0 endpoint returns an authorization code.

Always set the value to "code". Example: `response_type` = code

**state**: Defines the state between your authorization request and the Intuit OAuth 2.0 Server response.

The state field is used for validation. It checks if the client (i.e. your app) gets the data back that it sent in the original request. Meaning, the `state` is maintained from send to response.

You can enter any string value for the state. The server should return the exact `state` : value pair sent in the original request.

**Tip**: We strongly recommend you include an anti-forgery token for the `state` and confirm it in the response. This prevents cross-site request forgery. Learn more about CSRF.

### Optional parameters

**claims**: Optional. A JSON Object containing a set of user claims that your application is requesting via OpenID Connect. These claims are either returned in the OpenID Connect ID token, or UserInfo response. Available claims include:

- `realmId` —The realm ID of the specific QuickBooks company to which the user is associated. This claim is only populated if the user is currently logged into QuickBooks.

```json
"id_token":
{
  "realmId": null
}
```

### Create authorization requests with SDKs

You can create and configure an object that defines the authorization request with the required parameters.

Here are example authorization requests for supported SDKs:

#### .NET
```csharp
// Instantiate object
public static OAuth2Client oauthClient = new OAuth2Client("clientid", "clientsecret", "redirectUrl", "environment"); // environment is "sandbox" or "production"

//Prepare scopes
List<OidcScopes> scopes = new List<OidcScopes>();
scopes.Add(OidcScopes.Accounting);

//Get the authorization URL
string authorizeUrl = oauthClient.GetAuthorizationURL(scopes);
```

#### Java
```java
//Prepare the config
OAuth2Config oauth2Config = new OAuth2Config.OAuth2ConfigBuilder("clientId", "clientSecret")
        .callDiscoveryAPI(Environment.SANDBOX).buildConfig();

//Generate the CSRF token
String csrf = oauth2Config.generateCSRFToken();

//Prepare scopes
List<Scope> scopes = new ArrayList<Scope>();
scopes.add(Scope.Accounting); // add as needed

//Get the authorization URL
String url = oauth2Config.prepareUrl(scopes, redirectUri, csrf); //redirectUri - pass the callback url
```

#### PHP
```php
$dataService = DataService::Configure(array(
      'auth_mode' => 'oauth2',
      'ClientID' => "Client ID from the app's keys tab",
      'ClientSecret' => "Client Secret from the app's keys tab",
      'RedirectURI' => "The redirect URI provided on the Redirect URIs part under keys tab",
      'scope' => "com.intuit.quickbooks.accounting or com.intuit.quickbooks.payment",
      'baseUrl' => "Development/Production"
));
$OAuth2LoginHelper = $dataService->getOAuth2LoginHelper();
$authorizationCodeUrl = $OAuth2LoginHelper->getAuthorizationCodeURL();
```

#### Node.js
```javascript
// Instance of client
var oauthClient = new OAuthClient({
    clientId: '<Enter your clientId>',
    clientSecret: '<Enter your clientSecret>',
    environment: 'sandbox',                                // 'sandbox' or 'production'
    redirectUri: '<Enter your redirectUri>'
});

// AuthorizationUri
var authUri = oauthClient.authorizeUri({scope:[OAuthClient.scopes.Accounting,OAuthClient.scopes.OpenId],state:'testState'});  // can be an array of multiple scopes ex : {scope:[OAuthClient.scopes.Accounting,OAuthClient.scopes.OpenId]}
```

#### Python
```python
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes

//Instantiate client
auth_client = AuthClient(
    "client_id",
    "client_secret",
    "redirect_uri",
    "Environment", # "sandbox" or "production"
)

// Prepare scopes
scopes = [
    Scopes.ACCOUNTING,
]

// Get authorization URL
auth_url = auth_client.get_authorization_url(scopes)
```

#### Ruby
```ruby
require 'intuit-oauth'

client = IntuitOAuth::Client.new('client_id', 'client_secret', 'redirectUrl', 'environment')
scopes = [
    IntuitOAuth::Scopes::ACCOUNTING
]

authorizationCodeUrl = oauth_client.code.get_auth_uri(scopes)
# => https://appcenter.intuit.com/connect/oauth2?client_id=clientId&redirect_uri=redirectUrl&response_type=code&scope=com.intuit.quickbooks.accounting&state=rMwcoDITc2N6FJsUGGO9
```

Depending on the SDK, you may need to set up the configuration file with your Client ID, Client secret, and Redirect URI. Simply reuse the values from previous steps.

### Create authorization requests manually

Manually create an authorization request in your app's language. You'll need to call the Intuit OAuth 2.0 Server endpoint, generate a URL, and define the URL's parameters.

Get the base URI from the discovery document. You can also follow these links:

- For sandboxes and testing environments: [Click here](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- For production apps: [Click here](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)

Use the values from the `authorization_endpoint`.

## Step 9: Redirect users to the authorization page

Your app needs to redirect users to the authorization page via the Intuit OAuth 2.0 Server. This starts the "user consent" step of the process. We'll call this the "authorization flow."

The authorization flow is required when users connect to your app for the first time. It's also required any time you change your app's scopes (i.e. incremental authorization). Users need to grant permission again since your app needs to request access additional data.

Use the authorization URL from your authorization request, or use the following examples.

Here are example redirects for supported SDKs:

#### .NET
```csharp
// Redirect the authorization URL
return Redirect(authorizeUrl);
```

#### Java
```java
//Use standard url redirect-
resp.sendRedirect(url);
```

#### PHP
```php
//redirect users to authorization screen url
header('Location: '. $authorizationCodeUrl);
```

#### Node.js
```javascript
// Redirect the authUri
res.redirect(authUri);
```

#### Python
```python
//Using standard redirect
return redirect(auth_url)
```

#### Ruby
```ruby
redirect_to(authorizationCodeUrl)
```

Here's an example authorization request URL. It specifies the QuickBooks Online Accounting scope (i.e com.intuit.quickbooks.accounting) and adds line breaks for readability:

```
https://appcenter.intuit.com/connect/oauth2?
    client_id=Q3ylJatCvnkYqVKLmkxxxxxxxxxxxxxxxkYB36b5mws7HkKUEv9aI&response_type=code&
    scope=com.intuit.quickbooks.accounting&
    redirect_uri=https://www.mydemoapp.com/oauth-redirect&
    state=security_token%3D138r5719ru3e1%26url%3Dhttps://www.mydemoapp.com/oauth-redirect
```

You can review the authorization request URI using cURL. Here's an example:

```bash
curl -X POST '< Authorization URI from previous step>'
```

## Step 10: Create the UI that redirects users to the authorization page

There are a few ways users can connect to your app:

- Add a "Connect to" button somewhere in your app. When users select it, your app should redirect them and start the authorization flow. Here's a [quick guide to creating button UI](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0).
- If you list your app in the QuickBooks App Store, there are a few options. You can simply link to your app's website where users can get your app. You can also set up [Intuit Single Sign-on](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0) so users can connect to your app directly from your app page.

Since designing this UI may come later in development, we won't focus on it here. However you decide to set up the UI, it needs to redirect users to the Intuit OAuth 2.0 Server and open the authorization page.

### Preview the authorization page

This authorization page is where users authorize your app and give it permission to access their data. They'll see your app's name and the QuickBooks Online company they're connecting with.

If they authorize your app, the server will redirect them back to the redirect URI you set.

## Step 11: Get the authorization code from server response

At this point, your app is waiting for a response from the Intuit OAuth 2.0 Server.

If users authorize your app, the Intuit OAuth 2.0 Server sends a response to the redirect URI you specified in Step 7. The response contains an authorization code in the `code` field.

Copy the `code` value.

```
https://www.mydemoapp.com/oauth-redirect?
    code=4/P7q7W91a-oMsCeLvIaQm6bTrgtp7&
    state=security_token%3D138r5719ru3e1%26url%3Dhttps://www.mydemoapp.com/oauth-redirect&
    realmId=1231434565226279
```

**code**: The authorization code sent by the Intuit OAuth 2.0 Server.

Max length: 512 characters

**realmId**: The QuickBooks company ID. Your app uses the `realmId` to reference a specific QuickBooks Online company.

**state**: The state value passed by your app in the authorization request. This should match the `state` value you sent in Step 8.

If users don't authorize your app, the server sends an `access_denied` error.

If the authorization request has a scope issue, the server sends an `invalid_scope` error.

## Step 12: Exchange the authorization code for access tokens

Your app should send the authorization code (i.e. the value of the `code` parameter) back to the Intuit OAuth 2.0 server to exchange it for access and refresh tokens.

### Exchange authorization codes with SDKs

Use the example code to create an object named tokenResponse. This automatically exchanges the authorization code for access and refresh tokens:

#### .NET
```csharp
// Get OAuth2 Bearer token
var tokenResponse = await auth2Client.GetBearerTokenAsync(code);
//retrieve access_token and refresh_token
tokenResponse.AccessToken
tokenResponse.RefreshToken
```

#### Java
```java
//Prepare OAuth2PlatformClient
OAuth2PlatformClient client  = new OAuth2PlatformClient(oauth2Config);

//Get the bearer token (OAuth2 tokens)
BearerTokenResponse bearerTokenResponse = client.retrieveBearerTokens(authCode, redirectUri);

//retrieve the token using the variables below
bearerTokenResponse.getAccessToken()
bearerTokenResponse.getRefreshToken()
```

#### PHP
```php
$accessTokenObj = $OAuth2LoginHelper->exchangeAuthorizationCodeForToken("authorizationCode", "realmId");
$accessTokenValue = $accessTokenObj->getAccessToken();
$refreshTokenValue = $accessTokenObj->getRefreshToken();
```

#### Node.js
```javascript
// Parse the redirect URL for authCode and exchange them for tokens
var parseRedirect = req.url;

// Exchange the auth code retrieved from the **req.url** on the redirectUri
oauthClient.createToken(parseRedirect)
    .then(function(authResponse) {
        console.log('The Token is  '+ JSON.stringify(authResponse.getJson()));
    })
    .catch(function(e) {
        console.error("The error message is :"+e.originalMessage);
        console.error(e.intuit_tid);
    });
```

#### Python
```python
// Get OAuth2 Bearer token
auth_client.get_bearer_token(auth_code, realm_id=realm_id)

//retrieve access_token and refresh_token
auth_client.access_token
auth_client.refresh_token
```

#### Ruby
```ruby
oauth2Token = oauth_client.token.get_bearer_token('the authorization code returned from authorizationCodeUrl')
# => #<IntuitOAuth::ClientResponse:0x00007f9152b5c418 @access_token="the access token", @expires_in=3600, @refresh_token="the refresh token", @x_refresh_token_expires_in=8726400>
```

### Exchange authorization codes manually

Get the base URI from the discovery document. You can also follow these links:

- For sandboxes and testing environments: [Click here](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- For production apps: [Click here](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)

Create a POST request to exchange the authorization code for access and refresh tokens.

Send requests to the `token_endpoint` (available in the discovery document) using the following parameters:

**code**: The authorization code from the previous step.

**redirect_uri**: The redirect URI for your app.

**grant_type**: This is defined in the OAuth 2.0 server specification. It must have the value authorization_code.

Here's an example token exchange request:

```
POST https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer HTTP/1.1
Accept: application/json
Authorization: Basic UTM0dVBvRDIwanp2OUdxNXE1dmlMemppcTlwM1d2
    NzRUdDNReGkwZVNTTDhFRWwxb0g6VEh0WEJlR3dheEtZSlVNaFhzeGxma1l
    XaFg3ZlFlRzFtN2szTFRwbw==
Content-Type: application/x-www-form-urlencoded
Host: oauth.platform.intuit.com
Body: grant_type=authorization_code&
code=L3114709614564VSU8JSEiPkXx1xhV8D9mv4xbv6sZJycibMUI&
redirect_uri=https://www.mydemoapp.com/oauth-redirect
```

You can review the POST request using cURL. The Authorization header should follow this format:

```
"Basic " + base64encode(client_id + ":" + client_secret)
```

Here's an example cURL POST:

```bash
curl -X POST 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer' \
-H 'Accept: application/json' \
-H 'Content-Type: application/x-www-form-urlencoded' \
-H 'Authorization: REPLACE_WITH_AUTHORIZATION_HEADER (details below)' \
-d 'grant_type=authorization_code' \
-d 'code=REPLACE_WITH_AUTHORIZATION_CODE' \
-d 'redirect_uri=REPLACE_WITH_REDIRECT_URI'
```

The server returns a JSON object. The access code is the `access_token` field value.

```json
{
"token_type": "bearer",
"expires_in": 3600,
"refresh_token":"Q311488394272qbajGfLBwGmVsbF6VoNpUKaIO5oL49aXLVJUB",
"x_refresh_token_expires_in":15551893,
"access_token":"eJlbmMiOiJBMTI4Q0JDLUhTMjU2IiwiYWxnIjoiZGGlyIn0..KM1_Fezsm6BUSaqqfTedaA.
dBUCZWiVmjH8CdpXeh_pmaM3kJlJkLEqJlfmavwGQDThcf94fbj9nBZkjEPLvBcQznJnEmltCIvsTGX0ue_w45h7_
yn1zBoOb-1QIYVE0E5TI9z4tMUgQNeUkD1w-X8ECVraeOEecKaqSW32Oae0yfKhDFbwQZnptbPzIDaqiduiM_q
EFcbAzT-7-znVd09lE3BTpdMF9MYqWdI5wPqbP8okMI0l8aa-UVFDH9wtli80zhHb7GgI1eudqRQc0sS9zWWb
I-eRcIhjcIndNUowSFCrVcYG6_kIj3uRUmIV-KjJUeXdSV9kcTAWL9UGYoMnTPQemStBd2thevPUuvKrPdz3ED
ft-RVRLQYUJSJ1oA2Q213Uv4kFQJgNinYuG9co_qAE6A2YzVn6A8jCap6qGR6vWHFoLjM2TutVd6eOeYoL2bb7jl
QALEpYGj4E1h3y2xZITWvnmI0CEL_dYQX6B3QTO36TDaVl9WnTaCCgAcP6bt70rFlPYbCjOxLoI6qFm5pUwGLLp
67JZ36grc58k7NIyKJ8dLJUL_Q9r1WoUvw.ZS298t_u7dSlkfajxLfO9Q"
}
```

**access_token**: The access token for making API calls.

**refresh_token**: The refresh token for obtaining new access tokens.

**expires_in**: The time, in seconds, left before the access token expires.

**x_refresh_token_expires_in**: The time, in seconds, left before the refresh token expires.

**token_type**: The type of access token returned.

## Step 13: Decide if you want to implement OpenID Connect

Your app is now set up with OAuth 2.0.

At this point, you can also implement [Intuit Single Sign-on](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0) and [OpenID Connect](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0) to further enhance authorization features.

## Step 14: Use access tokens to make API calls

Access tokens let your app send requests to our APIs.

Pass the `access_token` value in the Authorization header of requests each time your app calls an API. The value should always be: `Authorization: bearer {AccessToken}`

Access tokens are valid for 60 minutes (3,600 seconds). When they expire, use refresh tokens to refresh them. Learn more about [access and refresh tokens](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0).

## Step 15: Refresh access tokens

Use refresh tokens to "refresh" expired access tokens. You can refresh access tokens without prompting users for permission.

Here are examples of refreshing access tokens. Since you're using a supported SDK, server requests and responses get parsed internally.

### Refresh access tokens with SDKs

#### .NET
```csharp
// Instantiate object
public static OAuth2Client oauthClient = new OAuth2Client("clientid", "clientsecret", "redirectUrl", "environment"); // environment is "sandbox" or "production"

//Refresh token endpoint
var tokenResp = await oauthClient.RefreshTokenAsync("refreshToken");
```

#### Java
```java
//Prepare the config
OAuth2Config oauth2Config = new OAuth2Config.OAuth2ConfigBuilder("OAuth2AppClientId", "OAuth2AppClientSecret").callDiscoveryAPI(Environment.SANDBOX).buildConfig();

//Prepare OAuth2PlatformClient
OAuth2PlatformClient client  = new OAuth2PlatformClient(oauth2Config);

//Call refresh endpoint
BearerTokenResponse bearerTokenResponse = client.refreshToken("refreshToken"); //set refresh token
```

#### PHP
```php
$oauth2LoginHelper = new OAuth2LoginHelper($ClientID,$ClientSecret);
$accessTokenObj = $oauth2LoginHelper->
                    refreshAccessTokenWithRefreshToken($theRefreshTokenValue);
$accessTokenValue = $accessTokenObj->getAccessToken();
$refreshTokenValue = $accessTokenObj->getRefreshToken();
```

#### Node.js
```javascript
oauthClient.refresh()
        .then(function(authResponse) {
            console.log('Tokens refreshed : ' + JSON.stringify(authResponse.json()));
        })
        .catch(function(e) {
            console.error("The error message is :"+e.originalMessage);
            console.error(e.intuit_tid);
        });
```

#### Python
```python
# Instantiate client
auth_client = AuthClient(
    "client_id",
    "client_secret",
    "redirect_uri",
    "Environment", # "sandbox" or "production"
)
# Refresh token endpoint
auth_client.refresh(refresh_token="refresh_token")
```

#### Ruby
```ruby
newToken = oauth_client.token.refresh_tokens('Your_refresh_token')
```

### Refresh access tokens manually

Create a POST request and use the latest `refresh_token` value from the most recent API server response.

Send requests to the `token_endpoint` (available in the discovery document) using the following parameters:

**grant_type**: This is defined in the OAuth 2.0 server specification. It must have the value refresh_token.

**refresh_token**: The refresh token from the previous server response.

Here's an example request:

```
POST /oauth2/v1/tokens/bearer HTTP/1.1
Accept: application/json
Authorization: Basic UTM0dVBvRDIwanp2OUdxNXE1dmlMemppcTlwM1d2
    NzRUdDNReGkwZVNTTDhFRWwxb0g6VEh0WEJlR3dheEtZSlVNaFhzeGxma1l
    XaFg3ZlFlRzFtN2szTFRwbw==
Content-Type: application/x-www-form-urlencoded
Body: grant_type=refresh_token&
refresh_token=Q311488394272qbajGfLBwGmVsbF6VoNpUKaIO5oL49aXLVJUB
```

You can review the POST request using cURL. The Authorization header should follow this format:

```
"Basic " + base64encode(client_id + ":" + client_secret)
```

Here's an example cURL POST:

```bash
curl -X POST 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer' \
-H 'Accept: application/json' \
-H 'Content-Type: application/x-www-form-urlencoded' \
-H 'Authorization: REPLACE_WITH_AUTHORIZATION_HEADER (details below)'  \
-d 'grant_type=refresh_token' \
-d 'refresh_token=REPLACE_WITH_REFRESH_TOKEN'
```

The server returns a JSON object with a refreshed access token in the `access_token` field.

```json
{
"token_type": "bearer",
"expires_in": 3600,
"refresh_token":"Q311488394272qbajGfLBwGmVsbF6VoNpUKaIO5oL49aXLVJUB",
"x_refresh_token_expires_in":15551893,
"access_token":"eJlbmMiOiJBMTI4Q0JDLUhTMjU2IiwiYWxnIjoiZGGlyIn0..KM1_Fezsm6BUSaqqfTedaA.
dBUCZWiVmjH8CdpXeh_pmaM3kJlJkLEqJlfmavwGQDThcf94fbj9nBZkjEPLvBcQznJnEmltCIvsTGX0ue_w45h7_
yn1zBoOb-1QIYVE0E5TI9z4tMUgQNeUkD1w-X8ECVraeOEecKaqSW32Oae0yfKhDFbwQZnptbPzIDaqiduiM_q
EFcbAzT-7-znVd09lE3BTpdMF9MYqWdI5wPqbP8okMI0l8aa-UVFDH9wtli80zhHb7GgI1eudqRQc0sS9zWWb
I-eRcIhjcIndNUowSFCrVcYG6_kIj3uRUmIV-KjJUeXdSV9kcTAWL9UGYoMnTPQemStBd2thevPUuvKrPdz3ED
ft-RVRLQYUJSJ1oA2Q213Uv4kFQJgNinYuG9co_qAE6A2YzVn6A8jCap6qGR6vWHFoLjM2TutVd6eOeYoL2bb7jl
QALEpYGj4E1h3y2xZITWvnmI0CEL_dYQX6B3QTO36TDaVl9WnTaCCgAcP6bt70rFlPYbCjOxLoI6qFm5pUwGLLp
67JZ36grc58k7NIyKJ8dLJUL_Q9r1WoUvw.ZS298t_u7dSlkfajxLfO9Q"
}
```

## Step 16: Revoke access tokens

If users disconnect from your app, it needs to automatically revoke access and refresh tokens. For example, this process can start when users select a Disconnect link or button somewhere in your app.

Here are request examples for supported SDKs.

Send the request to the revoke endpoint. This both revokes the access token and removes permissions.

### Revoke access tokens with SDKs

#### .NET
```csharp
// Instantiate object
public static OAuth2Client oauthClient = new OAuth2Client("clientid", "clientsecret", "redirectUrl", "environment"); // environment is "sandbox" or "production"

//Revoke token endpoint
var tokenResp = await oauthClient.RevokeTokenAsync("refreshToken");
```

#### Java
```java
//Prepare the config
OAuth2Config oauth2Config = new OAuth2Config.OAuth2ConfigBuilder("OAuth2AppClientId", "OAuth2AppClientSecret").callDiscoveryAPI(Environment.SANDBOX).buildConfig();

//Prepare OAuth2PlatformClient
OAuth2PlatformClient client  = new OAuth2PlatformClient(oauth2Config);

//Call revoke endpoint
PlatformResponse response  = client.revokeToken("refreshToken"); //set refresh token
```

#### PHP
```php
$oauth2LoginHelper = new OAuth2LoginHelper($clientID,$clientSecret);
$revokeResult = $oauth2LoginHelper->revokeToken($yourToken);
```

#### Node.js
```javascript
oauthClient.revoke(params)
        .then(function(authResponse) {
            console.log('Tokens revoked : ' + JSON.stringify(authResponse.json()));
        })
        .catch(function(e) {
            console.error("The error message is :"+e.originalMessage);
            console.error(e.intuit_tid);
        });
```

#### Python
```python
# Instantiate client
auth_client = AuthClient(
    "client_id",
    "client_secret",
    "redirect_uri",
    "Environment", # "sandbox" or "production"
)

# Refresh token endpoint
auth_client.revoke(token="refresh_token")
```

#### Ruby
```ruby
trueOrFalse = oauth_client.token.revoke_tokens('the_token_you_want_to_revoke')
```

### Revoke access tokens manually

Create a POST request and include the `refresh_token` value for the token parameter.

Send the request to the `revocation_endpoint` (available in the discovery document). Here's an example request:

```
POST https://developer.api.intuit.com/v2/oauth2/tokens/revoke HTTP/1.1
Accept: application/json
Authorization: Basic UTM0dVBvRDIwanp2OUdxNXE1dmlMemppcTlwM1d2
    NzRUdDNReGkwZVNTTDhFRWwxb0g6VEh0WEJlR3dheEtZSlVNaFhzeGxma1l
    XaFg3ZlFlRzFtN2szTFRwbw==
Content-Type: application/json

{
    "token": "{bearerToken or refreshToken}"
}
```

You can review the POST request using cURL. The Authorization header should follow this format:

```
"Basic " + base64encode(client_id + ":" + client_secret)
```

Here's an example cURL POST:

```bash
curl -X POST 'https://developer.api.intuit.com/v2/oauth2/tokens/revoke' \
-H 'Accept: application/json' \
-H 'Content-Type: application/x-www-form-urlencoded' \
-H 'Authorization: REPLACE_WITH_AUTHORIZATION_HEADER (details below)' \
-d 'token:REPLACE_WITH_REFRESH_TOKEN/REPLACE_WITH_ACCESS_TOKEN'
```

If the app successfully revoked access, the server sends a response code: `status_code 200`.

If it didn't, or there was an error, you'll see `status_code 400`. Review the error message and follow its instructions.

When a user disconnects, you can identify their company by including `realmId` as a query parameter in the `revoke` endpoint. You can use this information to show the user options to reconnect. For example: `https://myappsite.com/disconnect?realmId=`

## Step 17: Get new refresh tokens

Refresh tokens have a rolling expiry of 100 days.

As long as refresh tokens are valid, you can use them to obtain new access tokens. Always store the latest `refresh_token` value from the most recent API server response. Use it to make requests and obtain new access tokens.

If 100 days pass, or your refresh token expires, users need to go through the authorization flow again and reauthorize your app.

## ON THIS PAGE

- Step 1: Create your app on the Intuit Developer Portal
- Step 2: Practice authorization in the OAuth Playground
- Step 3: Start developing with an SDK
- Step 4: Understand the end-to-end authorization flow
- Step 5: Get your app's credentials
- Step 6: Learn about discovery documents
- Step 7: Add your app's redirect URIs
- Step 8: Create an authorization request
- Step 9: Redirect users to the authorization page
- Step 10: Create the UI that redirects users to the authorization page
- Step 11: Get the authorization code from server response
- Step 12: Exchange the authorization code for access tokens
- Step 13: Decide if you want to implement OpenID Connect
- Step 14: Use access tokens to make API calls
- Step 15: Refresh access tokens
- Step 16: Revoke access tokens
- Step 17: Get new refresh tokens

---

© 2025 Intuit Inc. All rights reserved. Intuit is a registered trademarks of Intuit Inc. Terms and conditions, features, support, pricing, and service options subject to change without notice.
