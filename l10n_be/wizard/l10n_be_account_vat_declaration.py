# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import base64

from osv import osv, fields
from tools.translate import _

class l10n_be_vat_declaration(osv.osv_memory):
    """ Vat Declaration """
    _name = "l1on_be.vat.declaration"
    _description = "Vat Declaration"
    
    def _get_xml_data(self, cr, uid, context='None'):
        if context.get('file_save', False):
            val=base64.encodestring(context['file_save'])
            return val
        else:
            return base64.encodestring('')
        
    _columns = {
        'name': fields.char('File Name', size=32),
        'period_id': fields.many2one('account.period','Period', required=True),
        'msg': fields.text('File created', size=64, readonly=True),
        'file_save': fields.binary('Save File'),
        'ask_resitution': fields.boolean('Ask Restitution'),
        'ask_payment': fields.boolean('Ask Payment'),
        'client_nihil': fields.boolean('Last Declaration of Enterprise',help='Tick this case only if it concerns only the last statement on the civil or cessation of activity'),
    }
    _defaults = {
        'msg': 'Save the File with '".xml"' extension.',
        'file_save': _get_xml_data,
        'name': lambda *a: 'vat_declaration.xml',
    }

    def create_xml(self, cr, uid, ids, context=None):
        obj_fyear = self.pool.get('account.fiscalyear')
        obj_tax_code = self.pool.get('account.tax.code')
        obj_acc_period = self.pool.get('account.period')
        obj_user = self.pool.get('res.users')
        obj_comp = self.pool.get('res.company')
        obj_data = self.pool.get('ir.model.data')

        if context is None:
            context = {}

        list_of_tags=['00','01','02','03','44','45','46','47','48','49','54','55','56','57','59','61','62','63','64','71','81','82','83','84','85','86','87','88','91']
        obj_company = obj_user.browse(cr, uid, uid, context=context).company_id
        user_cmpny = obj_company.name
        vat_no = obj_company.partner_id.vat
        if not vat_no:
            osv.except_osv(_('Data Insufficient'), _('No VAT  Number Associated with Main Company!'))

        tax_code_ids = obj_tax_code.search(cr, uid, [], context=context)
        ctx = context.copy()
        data  = self.read(cr, uid, ids)[0]
        ctx['period_id'] = data['period_id'] #added context here
        tax_info = obj_tax_code.read(cr, uid, tax_code_ids, ['code','sum_period'], context=ctx)

        address = post_code = city = country_code = ''
        city, post_code, address, country_code =self.pool.get('res.company')._get_default_ad(obj_company.partner_id.address)
        year_id = obj_fyear.find(cr, uid)

        account_period = obj_acc_period.browse(cr, uid, data['period_id'], context=context)
        period_code = account_period.code

        send_ref = str(obj_company.partner_id.id) + str(account_period.date_start[5:7]) + str(account_period.date_stop[:4])
        data_of_file='<?xml version="1.0"?>\n<VATSENDING xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="MultiDeclarationTVA-NoSignature-14.xml">'
        data_of_file +='\n\t<DECLARER>\n\t\t<VATNUMBER>'+str(vat_no)+'</VATNUMBER>\n\t\t<NAME>'+str(obj_company.name)+'</NAME>\n\t\t<ADDRESS>'+address+'</ADDRESS>'
        data_of_file +='\n\t\t<POSTCODE>'+post_code+'</POSTCODE>\n\t\t<CITY>'+city+'</CITY>\n\t\t<COUNTRY>'+country_code+'</COUNTRY>\n\t\t<SENDINGREFERENCE>'+send_ref+'</SENDINGREFERENCE>\n\t</DECLARER>'
        data_of_file +='\n\t<VATRECORD>\n\t\t<RECNUM>1</RECNUM>\n\t\t<VATNUMBER>'+((vat_no and str(vat_no[2:])) or '')+'</VATNUMBER>\n\t\t<DPERIODE>\n\t\t\t'

        starting_month = account_period.date_start[5:7]
        ending_month = account_period.date_stop[5:7]
        if starting_month != ending_month:
            #starting month and ending month of selected period are not the same
            #it means that the accounting isn't based on periods of 1 month but on quarters
            quarter = str(((int(starting_month) - 1) / 3) + 1)
            data_of_file += '<QUARTER>'+quarter+'</QUARTER>\n\t\t\t'
        else:
            data_of_file += '<MONTH>'+starting_month+'</MONTH>\n\t\t\t'
        data_of_file += '<YEAR>' + str(account_period.date_stop[:4]) + '</YEAR>\n\t\t</DPERIODE>\n\t\t<ASK RESTITUTION="NO" PAYMENT="NO"/>'
        data_of_file += '\n\t\t<ClientListingNihil>'+ (data['client_nihil'] and 'YES' or 'NO') +'</ClientListingNihil>'
        data_of_file +='\n\t\t<DATA>\n\t\t\t<DATA_ELEM>'

        for item in tax_info:
            if item['code']:
                if item['code'] == '71-72':
                    item['code']='71'
                if item['code'] in list_of_tags:
                    data_of_file +='\n\t\t\t\t<D'+str(int(item['code'])) +'>' + str(abs(int(item['sum_period']*100))) +  '</D'+str(int(item['code'])) +'>'

        data_of_file +='\n\t\t\t</DATA_ELEM>\n\t\t</DATA>\n\t</VATRECORD>\n</VATSENDING>'
        mod_obj = self.pool.get('ir.model.data')
        model_data_ids = mod_obj.search(cr, uid,[('model','=','ir.ui.view'),('name','=','view_vat_save')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        context['file_save'] = data_of_file
        return {
            'name': _('Save'),
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'l1on_be.vat.declaration',
            'views': [(resource_id,'form')],
            'view_id': 'view_vat_save',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
l10n_be_vat_declaration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: