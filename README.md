# ckanext-loopback

This CKAN extension synchronizes CKAN user and organization create/update operations with a LoopBack server.

## Install

1. Clone this repository into `/usr/lib/ckan/default/src`.

1. Install the extension into your Python virtual environment:

   ```
   . /usr/lib/ckan/default/bin/activate
   cd ckanext-loopback
   sudo python setup.py develop
   ```

1. Add `loopback` to the `ckan.plugins` line in `/etc/ckan/default/production.ini`. For example:

   ```
   ckan.plugins = stats text_view image_view recline_view loopback
   ```

## Configure

The following lines need to be added under the `[app:main]` section of `/etc/ckan/default/production.ini`:

```
# LoopBack admin account credentials.
ckan.loopback.username = username
ckan.loopback.password = password
ckan.loopback.email = email@address.com

# Make sure to use HTTPS for all these URLs.
ckan.loopback.login_url = # for example: https://loopback.example.com/api/MobileUsers/login
ckan.loopback.user_url = # for example: https://loopback.example.com/api/MobileUsers
ckan.loopback.group_url = # for example: https://loopback.example.com/api/Groups

```
## Run

Make sure to serve CKAN using the correct configuration file (`production.ini` in this case):

```
. /usr/lib/ckan/default/bin/activate
paster serve /etc/ckan/default/production.ini
```
