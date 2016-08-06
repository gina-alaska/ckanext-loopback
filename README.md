# ckanext-loopback

This CKAN extension synchronizes CKAN user and organization create/update operations with a LoopBack server.

## Install

1. Clone this repository into `/usr/lib/ckan/default/src`.

1. Add `loopback` to the `ckan.plugins` line in `/etc/ckan/default/production.ini`. For example:

   ```
   ckan.plugins = stats text_view image_view recline_view loopback
   ```

## Configure

The following lines need to be added under the `[app:main]` section of `/etc/ckan/default/production.ini`:

```
ckan.loopback.username = username
ckan.loopback.password = password

# Make sure to use HTTPS for all these URLs.
ckan.loopback.login_url = # for example: https://loopback.example.com/api/MobileUsers/login
ckan.loopback.user_url = # for example: https://loopback.example.com/api/MobileUsers
ckan.loopback.group_url = # for example: https://loopback.example.com/api/Groups

```
