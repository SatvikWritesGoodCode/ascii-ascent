from mainmode import MainMode

r"""       
  m   .m,   mm  mmm  mmm        m   .m,   mm .mmm,.m .,.mmm,
 ]W[ .P'T  W''[ 'W'  'W'       ]W[ .P'T  W''[]P''`]W ][''W'`
 ]W[ ]b   ]P     W    W        ]W[ ]b   ]P   ][   ]P[][  W  
 W W  TWb ][     W    W        W W  TWb ][   ]WWW ][W][  W  
 WWW    T[]b     W    W        WWW    T[]b   ][   ][]d[  W  
.W W,]mmd` Wmm[ mWm  mWm      .W W,]mmd` Wmm[]bmm,][ W[  W  
'` '` ''`   ''  '''  '''      '` '` ''`   '' ''''`'` '`  '
ASCII Ascent: A Platformer Game [Capybara Studios (C) 2026]
"""

# Create a spinoff, paste your save string here!
# Or, keep it somewhere else and directly paste it into the original program!
SAVESTR = r"""Gas2LbDr)_'uq=D%T]eX"G/MSY^sBXWYLWtas,i>KIsK)<Lo!PCl^I0"3LZO(8)fCNokV3,p%VE%C%Gq+0ueYIm%)(F8iYtIsh1g++<>"_p=+)-SP/Te]Z]]f?9AMn`N^?XOk3mJ+0B%ci7tGmJE+'^!`7[rUa1;mJA!klS#m,l1OW8c+&1E]tEqE55>!Bp5;!oSZ^9\?(UIaIei-B_b)"W5-j6kkjYGC3N!D(e^/a:)J@Z*VjAQ:Na]7.p!)2]_i(VQba6l5rnZ0ZoR+?bp\@t<pKoTOlg'>P5IeB#R@WbQS9abk2u\4'm/"hbs7u-<=hf@FC@\bl=ft:OWG4Fdotp0c`cAKa-7dY0@MH3e1t5@=l4TOg$.n@tqKeq*rPuJmLhP'PMlomVRq=-5fh/MbA?-\KN)=5l`I6K?2&=]3Zp`+*B\fVf;1qmU#FHfmd&O6PPIWP`ju1EYhF_`;\(]OkY1JH9e@jA*LZbeIPs!l[\`H,&h38J'fkQauZJ:TgV2\>N9<%Y(-"VOb.`$gZGi%dS2J_0-[aoJ=>'b66e,(39nMkKtg_Mh?EO7W=8AJV0[P\TA>K\MA`KnO9<c%kpU6MFn/0XJ+I-'L!W)T'S;k**LHCDHlEqsBS[1[o0_p>'g]]Ga#h\reJCLTVi@NO@hhOJA7f]r$Me?sJ9dU=0mkW4"iah_m<PpgGOI\eB;<2@g)XJI6&D3Zk[RS0YO!?]V[_tl:A6$\5YMhACEL9EaqBKg^VUat6RFi[51aJHnjmp]eH&R&=mohEhcAas20\%JT@n3CKhOfD*S]m+ZU8aOPHRcZZ_JY>NJ:-PaHd,KZY!:-&)1r%\<9I\fqgt5YMCt)sfb-c!jSl8PlR6=;p=9m`K"6N:B'a4nHegM]C<9PIgQ!.2IK^,7ec*X@MY/]J+buWQG\lSZ2=`]3<DA=Y[Ve+N4iXBCC#B+5BEHrq\;P@,*/%`>`hqFbfjOkp1lm91L+?7o1`C:>;`c0<caYT`_IBKp.<H=NB>Np'?k+Wlu/+hN5qri(n,DBNWg2tioTSRpG]lb"j7[K)R2nGB2fpp&eWuU+"`eIHT-U\=$>=uVRCD3'`f,32-)FE?:)^CUjW@f![4Xb+=ODf:0dSAMj&`h6F3]mc;5q$1_8]%b7-<u&9EUbhZT2Si(2m>Z?9UY%/i/u$f&tb<-<n0MV'Z?Y]o$/DjD7ML=9gJT?UZZ1:8Ng7d-kM:=:c+WrMPGH2H#A0Kj=*:$=AnI:HF1*qKO^%*B$4ZL=F\#BBiDLH6!dY(h3mnUq-KmZH:eoPMX(B58.UI7-Gh"6ec2DZ):<WF@2TDWK1,l\cCEfVcmf-s$M5ZsMbQH2(^E^0[c'7E4B`Q16,RZ"WKMuo9.2."B"ORSC4V^B;jeg*mMnab!F%#_hH3s:ohDPjV;n_eSBIobp'C89mZb@F<4@3U*4FQ'F`e>e9QX5bLoY^?MhI+l1kOl?$7tC_9d5:jh@L/JY#c,^gnpQYW]9>_HtQ8?bH^KnnGju]#;-!b5[$,bG=\9T?ssef3Fb<%COYc;(?4U>,LJ[rlM;V0feg(kL[#)&=JQRt7<B7*>bZ-/<N%7i8[I'W=j5Gqi=:Y/_K8q*9ld*EJI9O3aXX"LE2s=@3NGpU7*rL^=5@DG'.tO0L\R]6g?=f#6.*/8e-%D`KP;Kg+J+6k_]7?!S!(B+R-M.WXt\BJXZIY-haXi)"'X>R9oof$\WH[1]*8UV[%rs:AiG!k!VA8gWdT[Z^g/]n:)ST^R+#Nt@A5BmF-%27B3`r-<'8(0p!U]ZCIRYWUcHFJ9c@/]9q85k3Ej@5V8;#KDF;u-;1%4#eQ:WT6--pU(<"dGQlf/<R6k8s4*23q/<\d4NHMu\l<n+CMEFF]^m#e6(RK>V(79TY/on!L$D4#8A2$A)M\k@hG-GYB$e2LmHnBD%2OZ%iD/-LICCYb@jY6o[GToLD^cJW1*5%5*BFHmr+ccZT5.=d++HD>14,XKO51JIh@e"Tapo*=VFC^22+Hs^/$utJh^%U%57!I(>)`3V+=`iYV8*`''phcEu2Ku_APYT"Zneotc2,\4uVL:4e3)<q#MkiMXgt!</%e8J4nX2(c'QCX`&P.7V=\30cS@Ef^!O,uqX.\r33TMK"b,E7d_nPLPP4;kg/)nq4be->DUgkK4MJ#1pOjtceYn_CX2t$f3lB0[c^.EjDP@tcs3Tcn^0pa8E-&jeoMR"'1>1bg<:0_$B'L51dc6)<RSI`[ngs4#5B7VLAK=,jW!6pUrHT].N_db(@LHmK#bZkoH)=;BKP$phY8L8U9FAcRDc?(`"O31.+<[e81X,%6Sf<#Kb]a=[faL?[^0UZ>?kXibtl5hmaX?A0[50bql$Kjct'Zjb1)&7*iQ^^(^4+ba%h4it96raol-M%q]!!u\&b`Kmn1hei4Jp*r!SqoeU?p$TrP82#8SCVKIKM%G`_duL[\`-UT*B1[cfR:0aefI*bWm+'7Ae*F(]#rj&$RDn/p1/`a'(r&7NC[a-5aVBSjX.@VNDRJ''(NCoO8[=Sq<fWU^c[S],V0uI)IN]AVau><I?eY<bQK6WT#:a+Ak-,(d,.CTPCY0;JZYd1)CeiCkdm[a\]:.Qd\&F"Qm/eR.6>hSJ>p!;FZG2@.ZJG70V)#AcHLO?B?Hs?86S)Jq6FX$U<h+rgPT\t6ogdD&70VC;KGODJ`-WB5]QkA*n*6bj.+ei\I2NBLs_f4,GbY?9VMK5h>>CUdok!-?ar5tr8Fighq:-kc2Gi;VsC7A/l2+e[[42D%kld(hk'M[Zh)F7]70>7l_"'h>l3X)rN"i3f^B-!J%[s)g%g$elAN./ja@'i_:p!%cC<;K(]*7"BrAe&5'Z[Fgtpo4e+Kcb\)0;nD0Nm(Sb3BNknC`phsSP:YP,sHS%jH"IVsB,)lV6Yo)?](Vt9<![pMHbs2X5j5CGCrf]i$8hb60r]tX<E4ZhQWkR6hQcK2YkDsuBCk1-fmoh8.o]=U*%G/*XQbsulZb?U"2)%$l?BhoVRRZW=b(c!\?+7BR^/")7I,?I/!MDFikg$AJ1_g_]X<JaB"""
# Checklist [in order]:

# - Refactor and document

# FUTURE FEATURES:
# - Portals for changing game modes
# - Blindfold mode: cannot see map as well as character

__version__ = "1.0"

if __name__ == "__main__":

    MainMode(savestr=SAVESTR).run()
