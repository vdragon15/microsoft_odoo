# -*- coding: utf-8 -*-

import requests

from odoo import models, api


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _auth_oauth_rpc(self, endpoint, access_token):
        if "microsoft" in endpoint:
            response =  requests.get(endpoint, params={'access_token': access_token})
            print('AAAAAAAAAAA', response)
            
            try:
                response = response.json()
            except Exception as e:
                response = {'id': 1}
            
            return response
        return super()._auth_oauth_rpc(endpoint, access_token)

    @api.model
    def _generate_signup_values(self, provider, validation, params):
        values = super()._generate_signup_values(provider, validation, params)
        values["email"] = validation.get("userPrincipalName", values["email"])
        values["login"] = values["email"]
        values["name"] = validation.get("displayName", values["email"])
        return values
    
    def create_user_microsoft(self, values):
        SudoUser = self.sudo().with_context(no_reset_password=True)
        SudoUser.create(values).id
