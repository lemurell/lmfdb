# -*- coding: utf-8 -*-
#*****************************************************************************
#  Copyright (C) 2010 Fredrik Strömberg <fredrik314@gmail.com>,
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.
#
#  The full text of the GPL is available at:
#
#                  http://www.gnu.org/licenses/
#*****************************************************************************
r"""
Routines for rendering webpages for holomorphic modular forms on GL(2,Q)

AUTHOR: Fredrik Strömberg

"""
from flask import render_template, url_for, request, redirect, make_response,send_file
import tempfile, os,re
from utils import ajax_more,ajax_result,make_logger
from sage.all import *
from  sage.modular.dirichlet import DirichletGroup
from base import app, db
from modular_forms.elliptic_modular_forms.backend.web_modforms import WebModFormSpace,WebNewForm
from modular_forms.elliptic_modular_forms.backend.emf_classes import ClassicalMFDisplay
from modular_forms import MF_TOP
from modular_forms.backend.mf_utils import my_get
from modular_forms.elliptic_modular_forms.backend.emf_core import * 
from modular_forms.elliptic_modular_forms.backend.emf_utils import *
from modular_forms.elliptic_modular_forms.backend.plot_dom import * 
from modular_forms.elliptic_modular_forms import EMF, emf_logger, emf,default_prec,default_bprec,EMF_TOP


def render_one_elliptic_modular_form(level,weight,character,label,**kwds):
    r"""
    Renders the webpage for one elliptic modular form.
    
    """
    citation = ['Sage:'+version()]
    info=set_info_for_one_modular_form(level,weight,
                                       character,label,**kwds)
    emf_logger.debug("info={0}".format(info))
    err = info.get('error','')
    ## Check if we want to download either file of the function or Fourier coefficients
    if info.has_key('download') and not info.has_key('error'):                           return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
    name = "Cuspidal newform %s of weight %s for "%(label,weight)
    if level==1:
        name+="\(\mathrm{SL}_{2}(\mathbb{Z})\)"
    else:
        name+="\(\Gamma_0(%s)\)" %(level)
    if int(character)<>0:
        name+=" with character \(\chi_{%s}\) mod %s" %(character,level)
        name+=" of order %s and conductor %s" %(info['character_order'],info['character_conductor'])
    else:
        name+=" with trivial character"
    info['name']=name
    info['title']= 'Modular Form '+info['name']
    url0 = url_for('mf.modular_form_main_page')
    url1 = url_for("emf.render_elliptic_modular_forms")
    url2 = url_for("emf.render_elliptic_modular_forms",level=level) 
    url3 = url_for("emf.render_elliptic_modular_forms",level=level,weight=weight)
    url4 = url_for("emf.render_elliptic_modular_forms",level=level,weight=weight,character=character) 
    bread = [(MF_TOP,url0)]
    bread.append((EMF_TOP,url1))
    bread.append(("of level %s" % level,url2))
    bread.append(("weight %s" % weight,url3))
    if int(character) == 0 :
        bread.append(("and trivial character",url4))
    else:
        bread.append(("and character \(\chi_{%s}\)" % character,url4))
    info['bread']=bread
    return render_template("emf.html", **info)


def set_info_for_one_modular_form(level=None,weight=None,character=None,label=None,**kwds): 
    r"""
    Set the info for on modular form.
    
    """
    info=to_dict(kwds)
    info['level']=level; info['weight']=weight; info['character']=character; info['label']=label
    if level==None or weight==None or character==None or label==None:
        s = "In set info for one form but do not have enough args!"
        s+= "level={0},weight={1},character={2},label={3}".format(level,weight,character,label)
        emf_logger.critical(s)
    emf_logger.debug("In set_info_for_one_mf: info={0}".format(info))
    prec = my_get(info,'prec',default_prec,int)
    bprec = my_get(info,'prec',default_bprec,int)
    try:
        WNF = WebNewForm(weight,level,character,label)
        # if info.has_key('download') and info.has_key('tempfile'):
        #     WNF._save_to_file(info['tempfile'])
        #     info['filename']=str(weight)+'-'+str(level)+'-'+str(character)+'-'+label+'.sobj'
        #     return info
    except IndexError:
        WNF = None
        print "Could not compute the desired function!"
        print level,weight,character,label
        info['error']="Could not compute the desired function!"
    properties2=list(); parents=list(); siblings=list(); friends=list()
    if WNF==None or  WNF._f == None:
        print "level=",level
        print WNF
        info['error']="This space is empty!"
    D = DirichletGroup(level)
    if len(D.list())> character:
        x = D.list()[character]
        info['character_order']=x.order()
        info['character_conductor']=x.conductor()
    else:
        info['character_order']='0'
        info['character_conductor']=level
    if info.has_key('error'):
        return info
    info['name']=WNF._name
    info['satake']=WNF.satake_parameters(prec,bprec)
    info['polynomial'] = WNF.polynomial()
    #br = 500
    #info['q_exp'] = ajax_more(WNF.print_q_expansion,{'prec':5,'br':br},{'prec':10,'br':br},{'prec':20,'br':br},{'prec':100,'br':br},{'prec':200,'br':br})

    info['qexp']=WNF.print_q_expansion(prec,50)
    c = list(WNF.q_expansion(prec))
    info['c']=map(lambda x: str(x).replace("*",""), c)
    info['maxc']=prec
    if(WNF.dimension()>1 or WNF.base_ring()<>QQ):
        info['polynomial_st'] = 'where ' +r'\('+ info['polynomial'] +r'=0\)'
    else:
        info['polynomial_st'] = ''
    K = WNF.base_ring()
    if(K<>QQ and K.is_relative()):
        info['degree'] = int(WNF.base_ring().relative_degree())
    else:
        info['degree'] = int(WNF.base_ring().degree())
    if K==QQ:
        info['is_rational']=1
    else:
        info['is_rational']=0
    #info['q_exp_embeddings'] = WNF.print_q_expansion_embeddings()
    if(int(info['degree'])>1 and WNF.dimension()>1):
        s = 'One can embed it into \( \mathbb{C} \) as:' 
        #bprec = 26
        #print s
        info['embeddings'] =  ajax_more2(WNF.print_q_expansion_embeddings,{'prec':[5,10,25,50],'bprec':[26,53,106]},text=['more coeffs.','higher precision'])
    elif(int(info['degree'])>1):
        s = 'There are '+str(info['degree'])+' embeddings into \( \mathbb{C} \):'
        #bprec = 26
        #print s
        info['embeddings'] =  ajax_more2(WNF.print_q_expansion_embeddings,{'prec':[5,10,25,50],'bprec':[26,53,106]},text=['more coeffs.','higher precision'])
    else:
        info['embeddings'] = ''
    info['embeddings'] = WNF.q_expansion_embeddings(prec,bprec)                 
    info['embeddings_len']=len(info['embeddings'])
    info['twist_info'] = WNF.print_twist_info()
    info['is_cm']=WNF.is_CM()
    info['is_minimal']=info['twist_info'][0]
    info['CM'] = WNF.print_is_CM()
    args=list()
    for x in range(5,200,10): args.append({'digits':x})
    digits = 7
    info['CM_values'] = WNF.cm_values(digits=digits)
    if(info['twist_info'][0]):                          
        s='- Is minimal<br>'
    else:
        s='- Is a twist of lower level<br>'
    properties2=[('Twist info',s)]
    if(WNF.is_CM()[0]):                         
        s='- Is a CM-form<br>'
    else:
        s='- Is not a CM-form<br>'
    properties2.append(('CM info',s))
    alev=WNF.atkin_lehner_eigenvalues()
    if len(alev.keys())>0:
        s1 = " Atkin-Lehner eigenvalues "
        s2=""
        for Q in alev.keys():
            s2+="\( \omega_{ %s } \) : %s <br>" % (Q,alev[Q])
        properties2.append((s1,s2))
        #properties.append(s)
    emf_logger.debug("properties={0}".format(properties2))
    if WNF.level()==1 or not alev:
        info['atkinlehner']=None
    else:
        alev = WNF.atkin_lehner_eigenvalues_for_all_cusps()
        info['atkinlehner']=list()
        #info['atkin_lehner_cusps']=list()
        for c in alev.keys():
            if(c==Cusp(Infinity)):
                continue
            s = "\("+latex(c)+"\)"
            Q = alev[c][0]; ev=alev[c][1]
            info['atkinlehner'].append([Q,c,ev])
        
    if(level==1):
        info['explicit_formulas'] = WNF.print_as_polynomial_in_E4_and_E6()
    cur_url='?&level='+str(level)+'&weight='+str(weight)+'&character='+str(character)+'&label='+str(label)
    if(len(WNF.parent().galois_decomposition())>1):
        for label_other in WNF.parent()._galois_orbits_labels:
            if(label_other<>label):
                s='Modular Form '
            else:
                s='Modular Form '
            s=s+str(level)+str(label_other)
            url = url_for('emf.render_elliptic_modular_forms',level=level,weight=weight,character=character,label=label_other)                 
            friends.append((s,url))
    s = 'L-Function '+str(level)+label
    #url = "/L/ModularForm/GL2/Q/holomorphic?level=%s&weight=%s&character=%s&label=%s&number=%s" %(level,weight,character,label,0)
    url = '/L'+url_for('emf.render_elliptic_modular_forms',level=level,weight=weight,character=character,label=label)
    if WNF.degree()>1:
        for h in range(WNF.degree()):
            s0 = s+".{0}".format(h)
            url0=url+"{0}/".format(h)
            friends.append((s0,url0))
    else:
        friends.append((s,url))
    # if there is an elliptic curve over Q associated to self we also list that
    if WNF.weight()==2 and WNF.degree()==1:
        llabel=str(level)+label
        s = 'Elliptic Curve '+llabel
        url = '/EllipticCurve/Q/'+llabel 
        friends.append((s,url))
    space_url='?&level='+str(level)+'&weight='+str(weight)+'&character='+str(character)
    parents.append(('\( S_{k} (\Gamma_0(' + str(level) + '),\chi )\)',space_url))
    info['properties2']=properties2
    info['parents']=parents
    info['siblings']=siblings
    info['friends']=friends
    
    return info

import flask

@emf.route("/Qexp/<int:level>/<int:weight>/<int:character>/<label>")
def get_qexp(level,weight,character,label,**kwds):
    emf_logger.debug("get_qexp for: level={0},weight={1},character={2},label={3}".format(level,weight,character,label))
    prec = my_get(request.args,"prec", default_prec,int)
    if not arg:
        return flask.abort(404)
    try:
        WNF = WebNewForm(weight,level,chi=character,label=label,prec=prec,verbose=2)
        nc = max(prec,5)
        c = WNF.print_q_expansion(nc)
        return c 
    except Exception, e:
        return "<span style='color:red;'>ERROR: %s</span>" % e
