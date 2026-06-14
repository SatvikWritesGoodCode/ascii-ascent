from __future__ import annotations

from sys import stdout
from clear import clear
from time import sleep
from utils import IOUtils
from maps import GameMap, Constants
from typing import Callable, Iterator, Self
import pickle
import base64
from zlib import compress, decompress
from dataclasses import dataclass
from textwrap import fill

"""<anim.py> Reference:

- CutsceneData: An object that stores data for a cutscene.
- Cutscene: Plays a CutsceneData object.
- TutorialData: An object that stores data for a tutorial.
- Tutorial: Plays a TutorialData object.

There are some CutsceneData and TutorialData constants
defined.
- PLATFORMER_STR: platformer tutorial
- EDITOR_STR: editor tutorial
- INTRO_STR: intro scene
- ENDING_STR: ending scene
"""

PLATFORMER_STR = ('Gb"/lh/;#f\'urbdEIe/lHm-*jA9kR)Q6gmIb)5LE8J-\n'
                  '7FAJ@_`!XTD@75!YGg[W:,"O$5R7=k0(G@dA=H%fK<9cq1fI=U\n'
                  'Ghq>e3Bcckl0GIdWVOunHI?NWl)P!f4.B6\\m"q"<hA?[-\n'
                  'ACRf<./f_*Q44alrJn6c.``UhEJ4Z[oe_5H=kj5@,WhHtk!dGt\n'
                  "Z_NupM)T*/cW-V)3)JcDkL7o..>3'-2ir,ip]B@-\n"
                  '6prBOY1=2r2:ErAlAHuD)C)nPh$[;`($id3m_?+Oa,`n"Cj80R\n'
                  'K9Ns";:SA&@WpTm,Gq/)c_IIDtU5;o,UdEm^fH;7E2mjD_-hpM\n'
                  '5()?32irefF(j`Z(@;`"*GRIZht`bqf-\n'
                  '*kkD@Ih8QJ1fn$;LP@F^S%eWC:lP$6WilK3@qlLuEk88`QF:_O\n'
                  'p1UBllg+H):bT/Mp3c=;0JeJej$LEuoQecAgK38_&@Lt&QZd(T\n'
                  'C"K+<:qJPXlgEnOg%\'-\n'
                  'P1@3IjC2U`H<t0q&!Bk#XHbZ?lH_8$%:>\\8jnb>tShGe]Hn&I9\n'
                  'I]ms9@F*l+&UQ9M-\n'
                  '[`t*Kbkh4FYOlL&,JBsue6OOCl5igjdN!Tja),r9DMrALDR]ih\n'
                  'Zn7hf3<Rh%^#L6-\n'
                  "<5:[T5'`g8D:G=e[G#VmE'Z2,/V`6Q9+?RSZJ^`lL#B@QP.XCS\n"
                  '*D./G1=f&7d*HK>[pM\\(8gin#-\n'
                  ';srhLa4W>/0s[XKrA4u#Xf[]8,An>fMiOla@"c,;;>/idI>mo)\n'
                  "3hjb=J%4q]1K:N);M8>$8mD^g7+no'6&b^Z&mM8$YU`V!1JEbT\n"
                  'F#9u-io)OXpH_\'kQ73o-\\*P:$"sC/&5\'_]9%*p0._:-\n'
                  'Wnd1rqBEFWQ-A3"NM"3C=AJnc=\'DVdX">g-R5SHHj3(-\n'
                  '1m_53)CTS\\$tBEFWQ-\n'
                  'D1[="<=/ARc%(3(XPQ6!AjgO5SML4,>"=s<jG2Xc6kl?7Zp6(7\n'
                  'ZnNZ^`f_X#qef\\J0sgnTF#95RXc`<&o`ZldKGn>>sK)!"OI9.!\n'
                  "DPfm64#V>F_cSeecdmm:B4*S'@6k=+d@LEe<D;e.%lEE!b_Y(J\n"
                  '0poqT`c@0jtr3?H<WYTPX5@E5SMKIBk$GDEcO8`57Hs%IUerm]\n'
                  'B3IF2Ei0(4V-E@?9D\'Mp:7HnJu46"";39C!GZl;L4E#-\n'
                  "!\\jhlpT)(Tm[d13^A$qY5DA`n5V6a$IV*_>e'B!*WM[$d\\a6H#\n"
                  '73If_k`5t4n*48*-sMqbY8S3WKUHhM[7"P]/+e,-N-\n'
                  'j0D7bc2![Vu/NfVWAJRmKNP^k%;<K&qVGXR6Mu*>8Qb#SOIdVc\n'
                  '^B^33%l][ZthBLB[O99!E\\>oma\\*$:I/""G%BkkT^B;qLCcj&h\n'
                  'G,(HfCia5Ql1&&;VK[5*Aa8&*QA5_=BmoiCucC3[P-\n'
                  'N&3q=/.*r4k+dZU4T]5/;"LSk-\n'
                  '+%[l]ejfuABMJ&@:U#4CEUEo3[1Y_H8LVpjoHBQ/q4Q`i.hL3&\n'
                  '!.?,d5Te@.>_;\'iMVC9Z:b)S=Ob<daKQe2,?6QK9D2"/]oEhu@\n'
                  '[XoVP[V7Vde4YMX.^Bj*-\n'
                  'cfV#P6C"@ME2%^02`(=\'"dW252`4QhAW$I*oEFiP^!FJUh[533\n'
                  "n35/qF;1K]S7b?l4;!=9:KV_W<V'-\n"
                  '*V5eQNq#`e9"?N3B^Ab7(]dnH7kI%6ZGMo.dnUo!R]BW4/@NbZ\n'
                  '\\(+&HY/Aj_d!1[>:bI$;$7BaOV&#ss)a8IGQ[mop\\HjM&$<p\\.\n'
                  '4&q;GQCGK+6*ZFkf3B=!N>F#HO@uQt5q^q6OGcqeXK\\POZr8-\n'
                  '7>&#q%F-\\d)-\n'
                  '6PH:/u>fqQYCe3/j]lM_Nn6O:5)pg$]\\IA&3qkEioNuh*QTNcZ\n'
                  '%CnUa9Ca3.MXB8O@uQt5q^q6OGcqeXK\\POZr:t$==po`m$pBJ+\n'
                  'I?!rJm>fK+;^^S=^at(BrAO(E_/?bcm1of%UUSLj$a:UjAII6O\n'
                  ':/N&j<Bg2.r8oWm8Q+G(0b\\EEWl)7dF70!&i<pj&3qkEiWZl3H\n'
                  "U'2M$*qF6<msf,MfL7Ml6NU1L1_Z/,\\XDI/ka+jEoH_B>_E`#K\n"
                  'e9F(SU)(5Jg6Td#p>R4n\\V-\n'
                  'Dg`DQ8:kGdQV:DqOER(DH=orkB+U!m"WH^]]g`DQ8:kGdQV:Dq\n'
                  'OEOAn#[05id63n^#;Xo?D\\39=Pb;L#Q*#ngr^UfrhGMMq!&4DT\n'
                  'BeZ%gPV4o!"BBJfOIR<N^%3Ls:]PDQ=M!!oiVtJo@.AQZZL3GU\n'
                  "SEONJSoB>9V:7#u\\TCM&?G'r`h!A2'Y\\FdmUk9:3`Y$f:D2mj1\n"
                  '>]-i`]Y.mc3IOg+DD5@?Zf.P0%a"a<"f]OSO&`P/f-\n'
                  'W5rPWM3r=+qi7*E@`?!J4!;RX+XCZ9[X+HGp\\AY!0oeq9E:=`-\n'
                  '/]=D@j.mO.8WST#b[?n[Xh$roN%nY-io)OXqE@0-\n'
                  "j;)7!s)Aaf/?H^K\\d'$#USC?iDdp%-\n"
                  "\\+h[g.%H%^A..iHYRkL:5Nh`K[)Z#VZ'q@QnNf`IN<(d><ouD>\n"
                  '_.?Omp<6FHee@&.0T)frF/s$l$#j&hkNl^=_47J?Ki@5kh"Np&\n'
                  '$HZ3:`_hT.Fq[q@gk)diN@IZD8FiZ:6V/Rf9XNKSa#V4$7,3E?\n'
                  '+naZc>6NXqTZXaoJ;r,PMj^-\n'
                  '=$$072"gRejGqnG^&1hZbMddY!cpr^Ao+/e.gMaYoha7FoT\\,`\n'
                  ')[>_F\\4%@VF`r$j/Mbon]t(T(SFN_!(YoRN5A..BdNCJBoB:B1\n'
                  'mn^i&X\\0(:<Ha!"[).sY7,=6^6EK5p.I#RU-\n'
                  "(k'cn%B`8^=H'ZH:I8m6k0S7@AFNTLfSJThPQQ_cZ%c#V%>m9I\n"
                  '"eaqbcln,V+%IFrcq99jGa-XBi>Xg:V\\,W_>/@i,b"cPJO\\W1D\n'
                  "DZA=)JN1aG>H!t>/@apBI'&I)M(B;&8j>q(,XI>,jq7S6^4G[/\n"
                  'lcupN>*Re7\\Gl\'`%"QBg^6B+*5Ec#b2Map3(/$-\n'
                  'iNeD:@$*bYYQucmLKNNOaT%ueOWQh5X\\.U@#rk=A28Z2K:8!_9\n'
                  '"OIE2&r1G$Oh8t2X-\n'
                  "0u>!Y/(1NGp>@'540Q!Ajk;`$&0[OgXjY,??5^8;jd`HNF])Z6\n"
                  '%tfjV)m7&-\n'
                  "4lpO2N2HGf9>oj)Ceo8_cH0LT%4B\\0U;A)C\\&SNBe_.#WEZI',\n"
                  'kRb&pI-\n'
                  "e+f\\0[>\\8*[N>*Re7\\Gl'`!SBmP#%+r2YP^5EVBSUU:NM)7Jd3\n"
                  '/.7=/s^a!h)-Q[O>O0gHr]-\n'
                  'lMJ2<>EUZpuab,C\'F]#Wr`TE8m"0_]pbVipI+46qr#]9EL8c\'>\n'
                  "Pj^80#L'8,`UOZn.-I-\n"
                  'f>Onmu`9%n,bYJ\'EUf.&rAuW:a1\\D97G.=G"ADt.GR&eLT!e$U\n'
                  'g=N^TOUS;J4(NB3.qs%>SJcP`&EjL_])0N5eqAuftd=lK34pJ?\n'
                  'Y`Z@pUK\\,+996tS78iW6CW.Xr\\od[[OKm"2Ud-iBF!pmWLM9s`\n'
                  '&8iEG)V"g?Ro1$G\'D3\'$Th9]L\\bJa^6-&LGp?MU2@]*NhIj[a-\n'
                  "6/E?)UWMZ2StntT^;Q]3jdfZ#n)Ot%TA#nE/7u,,+3hd^2SN'p\n"
                  '&Mqn-TDS/R/B>?^!Of6:YtLG3(/%q+FuU>E;Bn!%Y:=)4+n5cL\n'
                  'u8aSJ,o!K(`KnO-io)/mJm7ni!t=3JNJMtE/<E^&:acK&/Z=q6\n'
                  'RVtj#jqZn#iH2DTn,:Y&o`Y9m[1];MDYH`JDg&55T^%p"+:G$i\n'
                  '"0J`K1hJ2XQSt"0)Ht$5d19;#hK==9)-\n'
                  'Z"q6IIBHDPO+jCPpGn7Rf4f,#5o`,]j+9Pqg""af\\^6%-\n'
                  "GU*'jZq^`I:tI.)MLq.Z$JOj8\\_3)ddoRa&)55&d!lqVg8lKCJ\n"
                  ';JI3ZGNUH1JC0mA!=eEs]P`T0\\<gl($Y;hRp:=u)SSajF4=j8K\n'
                  'NMAW&<diN4]Y\'!I!QgSK)L;tF=*!8GNl"gEQ\'!5cILW?HVi+fu\n'
                  "OrNR='&><T'%oG[^n&WoD8-\n"
                  'Tq:Z8_i_?G^Zh9$"mA5N\\dAha\\U5]rd[)g%_/8KRG0k*Y:k?*4\n'
                  '^rEmNp&_6mV&uC*K,mXGJG691Uh]4?Cs?(bT6l*$0piDE!P0\\c\n'
                  'kp^,g`\\e$]-\n'
                  'lP08T[J@&gsW]A%\'>sNEjd`9)s1[2?qq;G6lOMmKn,dE(:Ll"u\n'
                  '<]=SJ1EnBFMBQmLYu#h%T;Si/Sua%G4%`c3\\\\G1^;_9G6lOMmK\n'
                  'n,dA_^-erbS8iC+fX3::Of-1#NO=mRXqpAGl<(!KnjF[K')

EDITOR_STR = ('Gb"/lgN+X^<Q8$#Z^M3(*RUQ>[sB=-Uu%M>9-\n'
              '1>om+>RUgj=jr5[\\X@0JHuEeMb&5in`R2!Zq8?Dq%/TcX:7#Y8\n'
              '_rR0>RU<,D^jd*d2qi@M9\\kT$44WWifR8<-\n'
              ':qd^H"$F<d1V1lVgsLpLVo%s6TU2NK%=5s8-nc-bB<@F0E=r7j\n'
              '%TWPBT4jL"@E[n]B+III8ZcMtj,5O2%W"hL,3[f0=WUG"ch&o?\n'
              'gc\\a3fn"UGpL_n`[+9:!kik]RGK^:TtXj"26`n)Z!W=\'RZ_K]C\n'
              'r13bPl.u6J;3^<_s]2O=5p:T8fW(Oo#*)lMp28s*5RoUYq\\&*(\n'
              "@^,ip`7[mnORMlBS\\X^].#Sr@N?n6p:Ej*0.pnrp?'&Da19$Io\n"
              '?7F$$uP+lI"eTE*%P+(ZKBP"`M?E]qqj*7CIBV4ghFY\\/u3u"9\n'
              '&%FW\'3""<6kuj@sV]+"eSf;eN699XgaU\';k&_o9!;7nHlT20O2\n'
              "@+MPS=PUUN*fGrguTpZ/5BH>'7IBeSY!)>O(A]kqoR`X%,\\PF/\n"
              '"-8^J37*gLfJ7]dEFH;jECuAS7In-jkDY<k:cmXT%:IeU#I"O]\n'
              '%keN\\=Lm"gm3o[i^AI+O#K\\15K?Se?8o[`I1%)B/q@L-\n'
              'qG)#3*5rM;-\n'
              "k[3W\\dEY6r[$q*Sq*0$3sP_'KB(.R]8,eC!]D/Ef(90-\n"
              '9D<a._WDIhlD>tGX#_-\n'
              '7JKIq.)H54Id8EW22.VMpiKb;_&.WrK%l!S-\n'
              'W1gY!)tob4@;Os;h+PGTR\\cp`WX$XmNN*:<JD=o^k@K1Lk=NF!\n'
              'K&p(5*[O\\l,nMXJAP1A*@R.A@%p+e*sua%EXrL,nDI:V)?L7r#\n'
              "tKPrQl'E;:BF^oQ^C<qgI\\/!;&N119K3CW_o/M]@%pO1'L4tA$\n"
              "Fir9D\\r8d6sU:QM>f5LXoauh'SQ&8<t6\\]$IG8]'_mH?8To2B5\n"
              "YL_f'2SZ4DWD-EK7\\\\l@)566%Y+kGh?4%RC'6g''L75M!546'0\n"
              'N$H.mK4-*:!fQ;#I+Gk/cZP]!!P:-\n'
              'Rm:nd8jU5*#rCpib(,?>*-\n'
              'dGLmW!LlS#?`D5]=M:i$Tj2H5#C#:ma5#Sq$X>Za7utZWI1o*r\n'
              'V!T^MrntfqWcNf7GB2_e\\B]K]/e/$`#I*!)b9K$;q%!+[;m![2\n'
              '2l/a@e,H3<_(:[>kMoHW4)Xk](_O*tlL%eLRP+<d$-\n'
              'j?lB3`*J]Pl4/^t[*B!`Zk;L"DBBrH9iacI;(9qtaQ:%.(o\'`]\n'
              "3HctFJ@L<sin%OR916(#lQ37m%'TRe0r4-\n"
              "3F,6TIJ_KSo!W7(nZhW:CUTE(d,'S$naNR<)NaJdQ#%_2'Z-\n"
              'j167\'TN6VK"Wmj\'VUIH]m+"F?TBM;\'S$mX!g&#I0nL)R\'\'aS=_\n'
              ':\'Cb!X_1"7fc/shAANc)\\VH.QKL8I!X_1"7fc/shAAP91aLT8/\n'
              '^JL""r)S%NWP;o]eP*Q:.V>4>Ft#n"r)S%NWP;o]eP*Q\\WBXc[\n'
              'lht;"VcJ$NWP;o]eP*QKg;3kcbVk3%cf#<.6n4@NDUrM3b\\+X.\n'
              'VP2Ge<:k;JHQ-!"\\9f00o@61N&o4\\5tDL<ed_jD"X!t>+eUOs-\n'
              '&%:=c(mX!%N#9T5RL!^8AX."`KEPWSS$7l-\n'
              'jOPh"X&Mo!2O"@N$(Qc!g&!gTE(d,\'S$naNDV5U\\49jZqS]aY-\n'
              'n$JD.6n4@NDV)Q\\<#e3Lpi7c!!OJK80O]^MBmn/1ISe>["KDaJ\n'
              'HQ-!"\\9f00o@4[VZQ:ec>_kc"VcJ$NWP;o]eP*Q\\_sX>\\=86_-\n'
              'ib\\9"X!tq@g"6Ni4_8omLY`i\'S$mX!g&#I0nL*RE8PXSG9(l/$\n'
              ':"qg!D(&`(dSKJgp?c`-\n'
              'DOg2!D)/t!%HP>,=k,:4YnKu7kFiXJ/""FOFk/#JeVYPN*$8fK\n'
              'r[/FbX!DF!2OQJJ/%@0&Ypg5VVW%=>ik-\n'
              'W%Mf*Q5RL!^8AX."]dLcc;sILOajo>+je*ll!2OQJJ/%@0d;r3\n'
              'M1o+FmPhn:9ZQ,3!>6RfT%95_QW/<9%l!+7N!FuILN*[a(Zl/P\n'
              '8T].k.?KIh(TE(d,\'S$naN=hso;uffq"r)S%NWP;o]eM:*K"FL\n'
              "G:0.W6#Z:Y#J.r&',9&(.V^hiVTYOD);LfG_)PboZ:J_#pneHZ\n"
              'h?BKio^/eB]O9,c^5dUTSU.8,2e`f7g+a9jgUjrLp&?W_a;UcH\n'
              'GSk)^cVu>gX<!5_m"]-=G5sM/Y1=KNmU:s0Fe#0-\n'
              '_$B,!`5QMSg/#XspI?:2V9RG0bW!JIdUjrLpOIuTL!%D)"?jr+\n'
              'u$D9Ym!fT<OoLV;X"=]uD$:HD[&T&N8(=3ma$7LE+d0b7E7@aK\n'
              'uq@kn^[V^iR5G8&aA1.F,]K/g(h5:g.jdfY$8uW@u!!OL!GGM0\n'
              '9^_jRK+K#;?*)m%T#Z:Y#J.r&\'UXu8:giXO:WXL9U.3&L6"aa`\n'
              'YUc8b>S%\\[K^XE/]3dgX)nDnS6NS&4ugscD="c9u$)YUA[\'iZ=\n'
              '*WuNsN<A4ef;3a_>ki;/@W2l19fd$1FK:WdiCod7-\n'
              ':fk\\OW,(XSH=f^51oZi9e8s+.-\n'
              'jkDNVKX)[=*=2K5lGd]N,5?Id@VE_o2sQ/M>Ag=Sp[[n/O*qjV\n'
              'R4&NV;oW@1]?2%GHVVD%,-\n'
              "a+j`9?f9E\\l#h<j]5!I(BqMLpHt]P*2qjFsS&*<TgN28,/':Q3\n"
              '/f(XOEn$r7U/W7EgE]Z<B+J/>?o+*j!e/3F(haot(^+16-\n'
              ')r\\&Td!]"KmaDaTCL^\\A[)?iDm?OBo9FU!ds)*Xji.=_h.KTF2\n'
              'F!kjOb5u?K.XgH/_k\\BmSM5C81>S0.t"!*@j5u>q#!letL\\7k5\n'
              'GplL?0!&\\!n5#NU3oJJ*%6%Ki[d\\TEMLVnmX1^1\\RMXV2tk\\`3\n'
              'aJqC_?11X7DJYSpbiBoAh!oS#dp]um*d,V&="9i+:**rV8/NnL\n'
              '&7oOpYXpD7!6B_O6]N;mHX\\7>EE>=6>q.L,>_\\E2q88+/oLZ]#\n'
              'kmgtVBV>r\\_&Uq&r#^2F?Jc[UFpMmEIM#]M?&HIT>-\n'
              '4+X9X8o/"a[em"!$&-\n'
              'IJ3uYe"?8ME+9W\\78pn]J;h,dh#Tp$sPB%TG6%Kj(9B41b[K1-\n'
              'Q,(-\n'
              "1U''O+1$A&=4C*dapeLH(X=+lXU5Y%SH&/=c3JGTh\\\\.NVJ!&@\n"
              'dk4sD3XoJ.m"6%L,c&p%nH#\'f*an<"ON@PeFDK"e6BVh4%@L)4\n'
              'Q;$m<G&i?L+@5Sp1n&/=n9.kt=SMZ>D8&O,bPA/F8WHuJ`D2`B\n'
              'l,q!>EHalDk/&`c]sW<HU2SBR_ca5a8[8&6Q^[5CbQG)h0HMq+\n'
              ',>\\:T`q1=S`>b-\n'
              "%p#\\br0#D93e]3nDHG/Y90RG,aEd;r'6P+=jr`Wk'1K7ig^0.M\n"
              "sWEVkL9.47q86't\\N:[\\gW=-\n"
              'q(o?`p1$1;@$(Jb6*ni<,Z(c`.Su4N"V*n6NOm7WVWh"Q/NbVl\n'
              "o&Eg9Wt$l>\\3d&J2gI(C$Tp)'GTMM5M[6Tg*_gt:fTL*\\ZiYE#\n"
              '3X=8;c[`1R"&\'7C?e=T/SK5o_,\'B31SIScdaji3T*o=V4Jf6/O\n'
              '4Ig:VAhp-\n'
              "L0M#V[Rp!p;En']CV4]R@#V/BGF?u<QbiT(qA7&=U-\n"
              '3=U,*4bB!3k^!9aqH\\#WD;C?De85B[\\tYk3ndK"5El8l.sIIOO\n'
              '?c:D3(/tqDd;Hjj+]<J2e6=2`:^nOQ(!VH@VTW!ha1kSrQeBKT\n'
              '4fYmY150MC63174H"]E0F3#goT)Ul(s7iMjm"R?`/7Er2JZ^i+\n'
              ">gnE!+nV'EC(mokpSb-EQOjFK^il:HS[//4oqY^m^bpY\\)Fg9b\n"
              '16GH.LJhDRrokT-p31CDNas2.0-\n'
              'R!Ec[C^IB\\g_MXpZpCd:c`"N-\n'
              'qU(i+^TZJV_BNFTOFC%C;!DR.7VL+0t8`C&,Al/n#"46*C!&Ub\n'
              'NBV^5,>jTp]YE(n849<SU8c`KgR@F=Tjs&WLNiVAYPUYqFFK^`\n'
              'i6TbCl/4oqS5ae,D;!&sM)6&i,#=(s)!Q6N]!FgSHS,shq@NCk\n'
              '3X6?R>.<K.4(WW-hScE48V#W589MPU"F0T&1<5aFln>5.F?P]J\n'
              "g0AoJu!Vg]_/kh%#FEP=)S$_9tPk!pk-bu';.GtU/P#D@p>dXM\n"
              'TPqUr"PEcuV!*g;9!%rdp:\'\'9nn]jc\\<I@rZFPD5+PoH:p?P]J\n'
              'g0AoJu!Vg^*cAPZ9F<sU]@X%rn=d/ut!%p88lT*GV9[?K./$WF\n'
              '[M-\n'
              'A2CCsmK2k^R\\,KKg2J0F2SqV:$[KQjTnJQ0F^4bTEl+oTjg)bO\n'
              '7X^m^p$hHUQ0gVul43IgI+%<1k^t.5"=-\n'
              '%Z(on8Ou:?;fP$"b5p-B[s2LR4Xmh+Zu/r2\'`;]^5P&-\n'
              '^qh4I5\\Wois4AkG"=,#1TBBfKZQsMqM9jkcCC1Ar]-\n'
              'R[fJ3(*<h$N;GSKjlQ\\B<oo$hPl`&CrjT4Wtm=?:#]&REpl)jb\n'
              'cH@um?j?_.+`JJ"#Vrs9?!,taPQ[7`A@kfZ`(#+6ZEg1`:IiRL\n'
              '#t<#)dUpfUurr!E^Bfj+b^tTeJ*q&q3DeAQ2"3;`!qAN7"UNr:\n'
              "nqM^?1\\;_8b'.+'Mp1X7/V^/7K)Wf,*i/B:P_t_Jh]NP>bE#[>\n"
              '6,!2Jdb`e;UY^J6i[fXcjc,>!"eB4+tZ9\'\\qWcK&HL_.Z3I/W1\n'
              '(2_p!>.9;\'9TBs&Fg;UFb^"5&LSHT!KQ4BSIsN^4QAu_kXAhuB\n'
              'lt]:M\\3)&q@/I8,DAC47(*/9UgK.h4<=Ke!%$rbP3gdKpitR7:\n'
              'Qboa-B(/H:uE?lW^L6N$U\\/Fa^C&bjiREn,o-\n'
              'I.!^I@$!\'nBR>6>A(i9[SW2?B6t#&#2e!GLI;9rcY">MfRM,dn\n'
              '*n1ncg--At)C:]QaTM%Xo(=sS_TJ<H&q8n9FP8oW-&QO2P1-\n'
              '9,\\e<Y4lu>i:EK"eK]:kArLl!p=Xdo>)8/8M4t=M/3@oTqn]3o\n'
              'n\\dr$b``CQ_[JH?0MJao(cZ%THk==M$sQg(@oX88TbdBW`RWWH\n'
              '?S-q!DV;2K/#WT>_".^\\<$!Y?H]NOa.stGPJq\'_-M`$C`qmu-\n'
              'A\\le.Au_]s-\n'
              'Na^K5V(204]O_ql2.d7SWpNJBVmpLL$J(UB5oebposVUS^>S0\\\n'
              'OV0+O-8`9:Xi1Bitdp-alTF/r\\[tp&*ZaPBd35gKGcS/Ba\\S4E\n'
              'T;WD2R13:q!>W)(eF_%kN+f3#6\\*kO.q)aRJ!kF"Ip[k\'R[TYd\n'
              'Kt7(Pmo-\n'
              'l!oUt\'I,H34G/6b3KeY2M&:[<F!"(h686,3JOW^cDFkJW<pkPJ\n'
              '7!r,:g*=sW$#6hn5n+^#UdR4Y"<=h26:]LYV$@4!h<QXNa+P#?\n'
              '+[im<E#M26Q$M6WW?l]sV7?BS-\n'
              '%u<2LKJ<Ih1sc\\_!_Ea!l?A:#WBU-uX+@?`:\\+`X\\-\n'
              '2mW:`r"(pUG9erV!6=;HpoPOo.[WN2sgXV]-S+\\_cH-\n'
              ')?:I3$KRLorZ(]UGTB%`Xb/FJ!X0AW63.e](&14Z.L"ZL)3JWJ\n'
              "!0/BTr5jHj-ic4,NeM>t?N;(h9ArYN'L2]7!H9T+MuEe9.#XMI\n"
              'VE!3/"k"+c*#t<>Q](&:*$s6F3<E;^!,qoX:p:uJ!02NE;>SoC\n'
              'Jtj#!4ZCLR1]SKq#8F7p!e@%AE)caPTAZZ`7^#Ol.Ldo`eNF7g\n'
              '.h;$l^NIGa-\n'
              "5HbL'q5_lJlh=ak8^cU3(dQWKCmQ0VN60O^?BdIS!#+%T?Y,r?\n"
              '2YU<"+!N$qM)Qrh+f>?QpedHGlI\'@h<oS>T$e"Y"HQ^\\Z?i:6f\n'
              '\\qACJhUDt?AjEe@eKV(HQK@rRGMM8b,,r2Jj57Xn#J9RZ/e5FX\n'
              'fgK*H;dXC5Wm0i;cj38G*-\n'
              "'1&@Q9kRUHP!1[E)3Ao&>_kr>tmY=N:)(t/;9MK*sFO@)?l.X_\n"
              ",5'`;?$J,Ud[-p)DSr>GjKmISl!NFkHaX#(nY.pJbuPu[-\n"
              "cR@^^QWRa645>;G_1:'tAATLP/bNKb^<0&E-\n"
              '27,/4VB:`HVbP((q7@P1At?u,(h9[]],9E_;OJK%Gu@c>JN/d(\n'
              'n=`eDE+Al1?(FU(EPEYWB!.^[[>7DcH)@:,4m*k89]l"&mjcWI\n'
              '1SHXbWF]eIPl$=Iq/ZDi3=/DD4A!bB3)*=]CmTV&?>*q912c`S\n'
              'hJ&GR/pY=.N;7[8e6aFF?rsMp,h%qCbl$4AOVf&#.li&jra4?b\n'
              's.)=NTBtP:2IrPIf&]"g:"sJ@2=<*N`msRjK=+tjfE_7BqJ:V5\n'
              'pei7:cA!p^E]2u(k*pZoi\\[So^tc#aA,_)Z&hCP_q$/?%YW&0-\n'
              ')n"qFS_+j$3oA%>*S?i\\(;ELEgP(0+!;;-\n'
              'n%J:\'1!qrL6L1"q7dfXqA@Xi90Dk(edj)hZ;ad`k-\n'
              '%C\\u4gP(0+!;;-\n'
              'n%J:\'1!qrL6L1"q7dfXqA@Xh_@hDjOR`p%/TP;sZ9)_>B8C\'41\n'
              ',K`[Qj]kO#\\fULUe^tsn"T.tWoHNSWD\\%UIJ]kLB[\'!O<s1B`&\n'
              '\'Ri^3$&c4B0]n*kJ]n*kJ]l=b%hDAjNp80`2YW!d"B3[G#HNST\n'
              'sHNSWT."K!Fc4K>:D0fT.7-\n'
              'r62p;WJflo$d3BAgS^^tul`/.o*F/JPDllqQdS_;<\\=#PLX*r`\n'
              'j/UbZrf"_th_mnl;FB2prZ;rDIZ3^[:Z)HS\\apqY-iTHoZUs07\n'
              '@q,IJ!L&UK>l6&(3ri9cnd7]cj%C?/F_>k,5?+aa=]5NeE+:*M\n'
              "S%ej5MD&:9Zf(as67JgC1pde><Io8&YC3D0PWlcg8r:S#N$*5'\n"
              'sf-\n'
              '5"rH[V&.,YA$aD+9k&](4ABR:?u04e\\dK@EFp_=Q`hmm5?u0T,\n'
              '"(NQbJ$(t/FlLWbn2&2]a_gorfDb]Pq3apm1J$6/H2-\n'
              'g8qX<<6iPg4>h(VQDeB>6VRF-ShJZlVcJ?N[bJ0j,h>%\\,TVD^\n'
              "U,2'VbW8m`58G@JVG]TbCFRJgh-EtnOlHM$EZajI-WV;F?AIQ`\n"
              '+)RQgT,o[.+5)5oUi2[cB<\\^Pr-\n'
              '[7Ld&5o.40=PJO[4TPJ9.hhR_=9AK!Fb\\gmC=<97,@Z.?1N##K\n'
              'H?S\'M"#l5kIXeT1$NWtoak4gFD!Db>"H6(@%)LTGV?b+1`;Y]O\n'
              'D/c?]N"(_?YF2=j^_/=ZXYU)i;k"gF)\\Mu=nlJN0s!BN[J"&SP\n'
              ']k2$Yjm3F`aWCFep@,-9_nXM=r^6DK+1$b&PWes-bYd?YW@PLj\n'
              "Y]%>QE+PbM!DC6([*B5Q:MkF9Hpm>I\\.oJn%NGru%SnG:'sIf\\\n"
              ':?r>)iRF_0%S+J:X;oMgptkAfDf!e8nC_TnPK2W>niV-\n'
              "59e?n\\#R1P=8;mU+$!b'?r\\N9[Z3?Sl>V-\n"
              '_bWSejeB]@2K7u1#]5_XVQ%V2FX4m^MIkA9H\\+\\95;IBot"E]M\n'
              'hXh@5B<8,K*Pbo"f3p"($1K\'>LeP!ReFo/*,$4BTF[SZ&/MRf5\n'
              ',Q]<V3[:!WnV`mH/gm/fimckJ1V"-WhN,>(8j->03Es0/S-\n'
              "f4uifI&r's@W7:ZjDa:=,K)!\\aaqQbaaqQbacWDbXN:dXj:!Ud\n"
              ">&('Uhqgh%H5Ju-!Z2jnS$nN?4-\n"
              "mmV]1d?+FZqK;h#:\\u(BX:2@1!j1c+)E)jc^Y'VD^RG+[uKk%?\n"
              '(aT%?(aTN@Y6Bcb0oZDA\\ksoItq8"Y_hg2D@$C2D@%p\'JPKuS>\n'
              'sC#2P"O@cP&g);#ld^P67!NP67!n9>S3,S0W(8PjCMPKGXkH3B\n'
              'iq&Vnki1/f6NFi-+%%i-%L;=?!^Q`7AL7\\s,<[f-\n'
              '<mds*<T00aci^I!.SP!DEts%SVm2"m]oD1/6_n#WH2/C:Rl`#u\n'
              ';(%Lf".^"(SZhYpmF;gt3VsZDlZ2Z,$L]An_EX0;4OsDA\\jH5o\n'
              '_%;!K7JH%?(aT%?-8t"_\'-\n'
              'YP!j1)Rp&)t+[uKk%?(aT%?(aTN@Y6Bn)c"a4;+0&dnUQHLf"/\n'
              '9"-WhN"-WhN,>5kaR2fHu,s+mB+[uK+%SY/?\'6%-\n'
              'Enb&BiI6CGDAi%YiY>_dj)De)M3??M51k+DOnI*BPURn8WP+*B\n'
              ';G0cb9Jf!Gqpk@?aos#$@k@*M19c?Ib3<T3C?JC0a-\n'
              "4'jY!g]7g*<f-\n"
              'CSVtVk>N@b(2FUWt]gFll\\3"K61U4HiQ/B8Mp%OV)Qd`3!a17c\n'
              "qgEEkj;k2#&<0__<@oln:kLk60dmCqNNI'kSDjmTJVjVF7oq^p\n"
              ',gtbJbK7jRVlN="RKq:A1lePL#oNScG<Fi(u=B._/)12#@!Blo\n'
              'Hqe]#]rk;T^&VbOcApSUsj]jaL:IuCY&&P2h`s6eMEW%o\\,l*6\n'
              'A)j=n1i$68^8SOus"!r5BOL^+95KH;A<]:?VO"+@A]E)gMCr3#\n'
              ';<f7e`/<^9U9#<#2#+Pab_A.%tMh;;d41HU\\)fU=+&A8Y%lJN?\n'
              '`$FhMkVna-g$?->RegV;\'&s?+IU.NGm".Xt-Kn*2/Vbg4*9h@;\n'
              'J`dh!<;t.dUP`@"7p;&TmH0YI.!2n14^aUh6!)A)"i"Y)`r,rD\n'
              "T,71MqE(rZ2+5djk'J:Qe'UD\\uVna-g$?-\n"
              '>k$9>"\\3g,TWLJj=tG_h%X`"1Y2>mP+dE!caPgm!Ij?jo!u3!D\n'
              '9qS5[4jJqSi.<nG#`8BV[=Lh5#M9h@;J`dh!<;t/Nji&h1*$N[\n'
              '@>:8+>2S!%^tMufgVVr3P5^pO^=ZOkLKi"QM*\\1%`^^_h"tE!f\n'
              '[t.H#X^lam_TlJN?`$FhMkVna-g$?->R`$sUcNE9g;T[gk-\n'
              '\'GPLb&l+!4i"Y)`f$c)?2rt.3!h;Rn!N3/t!]UA\'J5^ts=:;$\'\n'
              '5BdfhKO5)fD,Q/k;rS!mX`"-SS(-<hW?E?^Ppjp[Vi-\n'
              '[dIPfs9UhZo&5ZRm/T57Ft.F+=4+K2M_%-\n'
              'ISme/3TY>E"c?XNT.FqG^JTeQ;MVrB;_ppI]*Gh(q17c-\n'
              ":I85&uE.RJt9A=sIh%R6<Q5P:hfX_Dfu@;bp%JU9*SQ*%'tkdh\n"
              ">ki^!O42(Rmh?.8>eK*[^[(W_ra'%k'BK7#p;4<qTFG,GJXO.9\n"
              "RZb<4H0OfZAI4'YaJ:ouGRd9SP1-3BIte4<Jnca&@<Hf[a3-\n"
              'mM7*G:HY^:fJK#Lo8pD`IT>\\t-\n'
              '_GBD?WLgB,"$WM),&*uSQO8&L,,WkN+p1?.i_LY)HU,pKelVb7\n'
              "eO[cabR54bZCF`/s.%rfD<k<c:QG::C:_iPU1U^Ua;]p\\aO'-\n"
              'F17amgWic6+(@]X/6Wr;\\DSmN&5WS)5`>cN\\*dB0<-\n'
              '66J^/=BXEB8cZRG=Sa)]cJ/o5[<CW[);:G0aok5BoKm+>NKNDc\n'
              '39Trap&$LOOZ=4PO;AXBA[?<^2=\\=b8WN.Mu>:\\!r<X-\n'
              "N+lr3%]M(m:PQ8IuhUFG,S>__$6+pQH+10nMhQ54!l>WrUu&'@\n"
              '^%U_h*l380,mj5`WOCS(!RQDn$uei&d:KAgTQt9)TK3-\n'
              "I$agblUspN%4,:T1UO#DI?2rleoP^BR3./6*I&:H.[Kh<XE';P\n"
              'Hdlms9mk!CqBon-\n'
              'F@\'2>59)"E76bp^[P?5m4/HifJ<g]uTYpJcW6+FrJW$=.AD3pK\n'
              'Vn;!-\n'
              'a\\_@J8_L!WRNIHT3("1Q0UaJ&L2;(tdnU:9;F!%\\%5&o[7.!(X\n'
              'i\'"+NSN4$%:?[hnpcXOSS&$P=,<b*C;SB!p-pt0^ZM)df-\n'
              "9/o?iT#5#3k!'n1tej24q+c\\OH$<S7!n#lrREi$n+Y<OWel=_E\n"
              'D!A"E6aQRS?46"@imTR\\(05-&Mfh>g&LN-I.U:P_<b;m-\n'
              '7\\CZX59eQo^,7cO;S1MYb6Vib;>CF:\'!L7A:hcMMmL"eKj4HV"\n'
              'YXo.b*Lb<>Vh^j%hDi+0)N=^&T]f$^U*Kt$_uW+4/QmHq49HCk\n'
              'B<@F3J:si&*0W\\]h%RqOu_0tlf;s[d>:$A[6BP0Bos:^,Illu5\n'
              '(9?;7G>$#X^+[#d)=9N\\2^=EH/&6g!h]kMo&T]NrI35K3$qeMf\n'
              "c'aRAjZVeiDbEi7$#j^RPaAtSj&:2K[)82[;.IEi*0oN-MQ?)_\n"
              "SlB?>1]<:*]PStb1',5rjMDFC_bSdmL^IC9^K4X>5G^<]4nS<)\n"
              "a;>]>l'b`OdY;oqNf#UM$^;J?Jqt(>1mo(fT&*UPf\\7!VCqaep\n"
              'Y]\\,)k&a!L>90GFAt5d6\\GAg%cs+2KTic[b1`I(cO/beokV1<j\n'
              "a2o>cPE1X0=Yi$UO@?6cUV'5Ei/,K3j^?/*e<_;qpN^mHjAPW=\n"
              'Bq*Z/J_F=!n?_QNqRnk4Wg"l35Kh.*IJ+L]@oO.qg.eGI^-\n'
              'obDp<M#[qaK\\rSF\\Z/K5KVU>S-\n'
              ".%_dSa?#:_RID,Ei`WX%%^0e;Iq[e,[hnaO+]orm.^'irtQ%et\n"
              'OpjTW3^Ou"5489<"GI)i9n"oZHr!U.3($qlYX>d>r.+L4pI;-\n'
              'an8X&O5b5D5()]STG3HU`4g7-\n'
              "UE$Wg5S@<T,I.:$:=TW55eQGg'ZddFT._AOZ/d*X9r\\,UHO^=5\n"
              '*@.$fOt?+m6fXemXs`GCASeS$EIo.QSoRo&e02cas#H"WCB/hc\n'
              'NKAa+jT(>ZO?WljbVV!IGTNksVu1\\d,uECTB-bt2$Mrn-\n'
              "$&BPd*^GSlJ)V>YA'hSdJ$FHa)VQ0_GODL[jk&[`\\sRQL<+BpN\n"
              'Er%F\'m<%(1,0bC4+leIo)T(,#c:Y5U11B"_"`:BC2);(T2b\'p\\\n'
              'rfOJ3j)Ahi-\n'
              "6iAB&lq_7?#:7]8($[[&h4mU;R?b<bO@:.lfI`G'),fmO9d+gS\n"
              'K+9butNDI,9VW2CORU5bDrH=R?l#$F.+KsGCmaPQ?S6d$aCkIs\n'
              'I9Z&:b$KNYoY*N:8f[o^OY_3\\oo7)1>.R0jT@#KOR:s`B3O(C,\n'
              "N^ec8<d$kGXC$7=D55e,9'#?2s?30O=BSuj4:p@<Y*pRAQ5$SD\n"
              'B*@qti#*+e>!7VRe76h;1=B^7YC@j?/,qTcM+[lFI+_Zc6*,DI\n'
              '&]3$dIrC(\\pVkKH-!`0!KBGMk!!I(g>Ece13)J(&U58-\n'
              "0_'EB*Q8$a?&$J<2Rkl;1F!<lkdW%G;elsR$PI:s1`K3eW;J:a\n"
              'KsJ4%[!=Y"I`G[5RUqROfCQDYH2m!o/A6dukP4-\n'
              "i^ihmI.57u7<*!t'Ph;-\n"
              'RRjnBo]B=Hs5>]+1r,#G+siYQG6J%T-\n'
              'F5ltEMoc^S;B+!h8E%k%EA6uA\'o_2!]5:\\6MTe<C/5M^Ioo"i,\n'
              'nl/HU=,<06`85`gEs"G)0!!Y@cH(0M<&E8Q!pl[Edd`+Hm8\\d<\n'
              'sR!=0laMguqP\']aQ_J4REULd47\'!?`S"Ml[(MHC[6n6p[L[_@)\n'
              'J_)4m-h5QhDo&Q)a8&8@hGYoa%-\n'
              'oGc]o\'GM:4,D*AF)K;M8RG8PlP]]DS3TB,;e*77"5QNhgC5[Te\n'
              'N=%.],="i8!L,i8;#sK;BT%[:M1hk19.@`5P$CUA/YG?8\'EBGR\n'
              "[Ko^XTV/G`!h/a#TEu;H'n@W_[YSmkoZiVOK)0?k(JP6>n[+%&\n"
              "-;X]2LtX&iBu7'HJL*ED=h#n+:Dr8+4b*S;!/dj0!h_@uO9q/7\n"
              '4%4`M]U<.5-\n'
              'id2]P\\*3:\'GSl_\'#Tt!Mr"93U^SMOa@,^Q##i05!2^%U,)Rg^i\n'
              'Hqn4^Tg*)_Ip%U:EH-VjSo74&eD8')

INTRO_STR = ('Gb"/j:N%1@\'Yn^PZmG:Z/qo0]*^V8,$7dT$j:YU4\'eG,>,*id,\n'
             '73/R=1/%A&[55htJ-\n'
             ':YEAT%t^ph"mV^\'/Gp]<.XNG_\'&T<F27tZ.HU+Ie._?^Y+J8j4\n'
             '8.trYt:gM7K*mME$Dc[WUS>N943*D+8!19QoGm7/4;0dB7g\\R3\n'
             ',,262M+^@8CXNDe*p;J]+e<p8^NA28Ea^%ub=iM6(]9acT`DZe\n'
             "'<erJ<]6(2`05;2Sdr]J\\#S8Z[r&HG3ahU8qd;QE7qI7r&RciE\n"
             "S&;'0$%mK>W=+J%%Xla@:@E@3EGJChsQ%n%&82r'Hn.OOp%-\n"
             "jI7s/XFEWL!dEh_cEC`)a`Y<tqTcW'YG=hPSM_';9@dL5UC&4O\n"
             "'/2`<]Ld9K*Yg&I.?>ZZ,nZH`Z=%t-\n"
             'GM$AV.M.\\(HIq3f4b7Dj"gdm(\\%dCg"MU*emjc]V$^@#"JE^A:\n'
             'RB5u7Y[=D)E7$=-\n'
             "SG*HhAQc6El8u:+5ns\\#iM9KWYEhZjKg]#abC\\hQhdMELW^,M'\n"
             'nJBBD-\n'
             "3VNR;8d$q2IUm`@!U7GfOBF^&D38ML>9<i&$pKHMUlE;'R?8T7\n"
             'q`^I\'V^pIC!cr%HbaNshg]b\'mliqlLV?1?"n<HUVpIGLd-\n'
             "Z:(e2_s`;CEBA2'fO8LiEJ`oM`^,?.7QNEuher2Sj*h.LdUr<>\n"
             "'pZ+@Y6^d.E/i7Q.R]'_k#Z&7H3)+Ul`cg/__@8#;BuUU8YE[,\n"
             '90W-?+^n-\n'
             'Hjm)fbZ)hTM839el)kE3t,PdN$0*<qgKAM")loqL"+]?@s8j`P\n'
             '6n+5&1I9JMKFYHcSt]WC\\4YOPmC@kIM.D!CUjC!]aS@=HP7lnb\n'
             'qKaYq6Q^)ZQIjqc^:Z);sG_?WOl>#1/M0L+]=2B#W`\\Fjh]t:S\n'
             '@W6\'Vj*Nu[Yrjq6"p-\n'
             '(Y!+h8DsGdf7<dRaP=;Jdf[>"`Qm>$)a8Rk*CfalQQkD[B3pSD\n'
             "gk&nq+'9o+p'T]-\n"
             "k1s=h1KajVZeCSJ0:^)H]fu:SS4oLelj'?LrV:.0I>f61lE^+t\n"
             '^O6K-\n'
             "n/;Omi;s69%O%6aoh+YZ>mZ<fL>+hFdj5D%Q:kU)dX2d'd,q;!\n"
             '-Yt#O$N$t<6k[r\\uLT[<eTA*="I]q_`iadd!^@uZjElXdD5RLC\n'
             'F)&EG?FehU5m)GJ*r-\n'
             'L@<1%.YVUCDBVI7IiqVucuQgX_8?^WWC.p4\\uijfokYB#trBE`\n'
             '?Jo?ihZgnJ=[[7e$H>EUdYOWq\'9ccXa(\'BU5a9,"E@P%45J7(<\n'
             '`Ij"Ku#ND0^9c;(bm>cn&=P7?/i+)GIpL/XAo_#[[Op8"8VF-\n'
             'A#jO)D#o.@F/B`-\n'
             '>9YHl:/"8AZN7MH)uXk=gA6i**!h4R",KHq3T2]k,a-\n'
             'jhkmK[?N')

ENDING_STR = ('Gb"/l:N%1@\'Ys#].7N7S2D%7c`jCg/`G4E3Th*6=OX=t8Ue4NR\n'
              'W/AO3)1/humo\\Fh;G/-`T^?<//-\n'
              'e0(.1kBf$PuQc!Bp`EZb)6gg9oO8kKQ%@UH#NlZhoY<n,;gs]A\n'
              'r?mIei\\u;sJ/Q^Z%sdgT:5-bXS#Rbl?AjVJER,ptcr_[)Q-\n'
              "[>s.c<&,pde2^KO>71\\'#F3-\n"
              'AtJnn%65TX8S!\\a/hpG0ZGc5GfXbkp[<SE=DRUAnl?0cRmjh<8\n'
              "P*p?Rj#]9eP$i<Xl),+'C]>rY/X,ad+s*.[2V:]feGgcrLKdU2\n"
              'a..H?@BM",(bNt_QIkX#j#LmQeN1AUa>a*A5oEMMQ\'O),+CV`G\n'
              'C)B1jM#*s_9Q!Ko\\d,@b8sZX9-MimjnW7`=-I#A-\n'
              'f!j<&lX9g5RUg\\lr`2/R)2XfJ6c%(aJMNUAQ2]#<^K244/9chm\n'
              "I7?V(&.]Qr3#Nb+'FW(Zi0j/M6CDn<loM<PS__jdZ=S[Jg-\n"
              "<:Y=^G:MtVL$ZEcYQgS<Ls95C[&ZUO'jHe8g=fsIK%NAS7fYGo\n"
              'k)or3[:iVprTEG]Ff6rZPQ9hU"mB>CU(!52J/85!^lJTmHiQ_\\\n'
              "A@PV:pK.1`)cfg>'D0aCeGAJ5[?2^8I*+hYpi-\n"
              ';+%j20T)lXttUlD=dWXmTKOp(8\'\'+*U;!IR(],X?4BL1",#7.!\n'
              '5]W/W&/i):s8^lJTmHiQ`gg.2Z=>\\umr]Red-OoR[W+p%U$JBn\n'
              'I^"K7=0&<*WKW7i*fI\'TE=2L6%PVbA@d*s_<2!0R>iOW&hHC*U\n'
              ';KX?KH"]a<Uq-\n'
              '5++T"8I6D8V#Mc%7*nGLtWu"TJh*0^o\'jOJ0,$cq#HQX[?2AZU\n'
              'pUfBIel<HoHo)aR7I<B%cHpZ,QVX)2$Dsf7aqq6"1?OG!\'Xs<!\n'
              'W4p-cNfO7W/]:<N*@5uMtDSSkY2&L16DQc*5L_>8-\n'
              "7:1C']hm)c;OcTi82\\5QIE3OT9hM^ukej!kHb1PVI[,.!TCdqG\n"
              'td6UZgT"*A2WF+<T=3VL+Tpb6>65H<(5#5:u$=QI-mfC<sGd7&\n'
              'ipEe_n]PloYr)ITq!0pLn\'#4BUAa.uRs*d:P"t4\'7I-\n'
              'F1FSncl-oZB)-.f/ZgUM-uK\\f)m1?V/eP!aYB,Kdb!i^]3O/Co\n'
              '37+(45F3EUZtP@T$Ff.6[`R.6)1m\\SWSLJ<FQGk@(Y@NlScGf@\n'
              '4UBurJ-\n'
              '>B%!\'VJi&u_hqT7ZpVW_.%.Hk/^X!r/":"RtFO4s*$&-\n'
              "uJks9Z@7TeJ2(U)58<h0[et*U8Wad3nn/oP'7iTZRW8^kpVTFG\n"
              'Ek$3;:O*_Wfb@4X70LU*Qo,2)fEB/rT:M)El[#_Ni85e>uKt?k\n'
              'ac[f)n0`"JrOMc\\RM-\n'
              '<CHeh\\oI%Fqh"2_>:\\%$V57ZWC!@0to]2!q@DFr6(flZ=DSm#Y\n'
              'hR#B]2RV=T]/su*ko8"-\n'
              "fiQ,`I^hFhGqmagrX1ZaKA;^oF?U5`WK9L_Y'fhRZRk9CTY%_%\n"
              "=URJS)6jBdFRE]o5#KL*:o&?NT3atV7'$tBYJ,.IlJtLU#(!>;\n"
              'Jn4`1I:_;+#$cIJhQoo-6i/[-a&*>4*,aN[,[[-\n'
              "Au(<)U1@gZsF8%g#L[B*un[&GQg.*3*CV2aRa&F`<]QT!'fiJ.\n"
              "@J7!i2'o).Im,A77eTA_&0Ss3LMA=]3uCGEk,T1RCCaWJ_U;t8\n"
              '"bqaKtOKck`$QUGE^&0,&ceX,4hS>RfeQ[.qER<e=N9mgmVj!B\n'
              '!AA*2:?-\n'
              'U5_BkORbh\\C#D7^ukt?!qF%@W\\H.8FY9V8WDnrV(SFk=2>nLHP\n'
              ':D0/YnV]$L2=^0n`)SL"QRbs=qdjImq$D66,k!.8`6#o?`P#L#\n'
              '0&AV%1([Fq;?3(7.s&(jes*!CiMr[D0?u6P@B,P""_agEnR]/`\n'
              '!Pl(&L<ua;a:n?k>T,o"(NS_]^t:thU,nB**^mBT^A:CZF!bLT\n'
              '?^!YmZQ\\NogQ/m>$Bc.X(tr)"@n\\OapA8BQONE#b39d@#n[R^g\n'
              '$\'hS-IJ]F+I(0R0\'S=W,`p=/6VBq9JT2)m"+mt\'hWoK/9"bu5l\n'
              'KR^"S;AA5?#\\&gO\'ieRTFrFc\'\\JU:0RB<b)+!JVRm!8t(6ZHns\n'
              '2B)?/d#Ub9`p":Ej1R^We)+sHh*C)=t[.mX%l_A($[Q]cD2#EF\n'
              'n?e9=k7lK!olX6mH@6j/p6<N;[7n1f*U2A%9_o9bC5ks)LLb.4\n'
              '9nY1Qn3jG&_>i%"/@=hK)X.\\R0<&CD(5k/HKRcTH7*-\n'
              'a5WfiYO!:/$"aXR8WG+WE(=-\n'
              'R"pr26FLH0Wgecr<4DDUr9(!`f#?h\'\\XM\'P&#?G3ErA4S"7cmu\n'
              'INT3uW89eeqISa-BZP8Hl!SPP8RSHoCF?mOSc+AfC\\\\=CK*&KF\n'
              "22[m4Ck7m[@7;0oMRH7-te'8-E9$mgu<8-\n"
              '4>VO"?@u"aXQ%fJF^aQRs#cY*E;PI!;KBn&nBe6+0-\n'
              ':,K*DF"Ap_B>_7UX3["X"Aenihk"$bKB!r?#9S<I10G8(<&BHm\n'
              'YUHG=&L0\\*.7I()M=sfX[/(?=pj<R-\n'
              '4!=:*2T]6CYQu3cRV9]28H<"@A"pE@+1MRDYjo5Q$ON<@')

type Pause = int | float
type StrFunc = Callable[[str], str]
type GameMapFunc = Callable[[GameMap], GameMap]

DEFAULT_SPEED: bool = 1.0

# --- Data classes ---

@dataclass(frozen=True, slots=True)
class Line:

    """A dataclass that stores a line of text as well as the
    duration it is displayed."""

    text: str
    duration: Pause

class Dialogue:

    """A list of lines that constitute a piece of dialogue
    displayed during a frame."""

    def __init__(self, lines: list[Line]) -> None:
        self.lines = lines

    def __iter__(self) -> Iterator[Line]:
        return iter(self.lines)

    @property
    def length(self):

        """The total duration of the dialogue if each line
        is displayed, one after the other."""

        return sum(line.duration for line in self.lines)

class Scene:

    """A class that consists of a map to display,
    a Dialogue object, and a pause before displaying the dialogue.
    It makes up one scene. Multiple scenes are then chained together
    to make a Cutscene."""

    def __init__(self,
                 display: GameMap,
                 pause: Pause=None,
                 dialogue: Dialogue=None
                 ) -> None:

        if pause is None and dialogue is None:
            raise ValueError("Must pass argument 'pause' or 'dialogue'")

        self.display = GameMap(display)
        self.pause = pause
        self.dialogue = dialogue

    @property
    def length(self):

        """Similar to Dialogue.length, read the documentation for that
        function."""

        pause = self.pause if self.pause is not None else 0
        dialogue_length = self.dialogue.length if self.dialogue else 0

        return pause + dialogue_length

    def copy(self) -> Self:

        return type(self)(
            self.display.copy(),
            pause=self.pause,
            dialogue=self.dialogue
        )

class CutsceneData:

    """A class that wraps a list of Scene objects. Supports save strings."""

    def __init__(self, data: list[Scene]) -> None:

        self.data = data

    @property
    def length(self):

        return sum(scene.length for scene in self.data)

    def __iter__(self) -> Iterator[Scene]:

        return iter(self.data)

    def as_save_str(self) -> str:

        encoded = compress(pickle.dumps(self.data))

        save_str = base64.a85encode(encoded, wrapcol=0)
        return save_str.decode("utf-8")

    @classmethod
    def from_save_str(cls, save_str: str, /) -> Self:

        decoded = decompress(base64.a85decode(save_str.encode("utf-8")))

        return cls(pickle.loads(decoded))

class TutorialScene:

    """A wrapper around a list of frames, containing information about how
    to run them."""

    def __init__(self, slides: list[GameMap], /, *, speed: float=0.5, repeat=1):

        """Takes in a list of frames as well as two optional arguments:
        - speed: time slept between frames
        - repeat: a number of times to repeat the animation"""

        self.slides = slides
        self.speed = speed
        self.repeat = repeat

    @property
    def thumbnail(self):
        return self.slides[0]

    def __bool__(self):
        return len(self) > 1

    def __len__(self):
        return len(self.slides)

class TutorialData:

    """Chains together multiple tutorial animations. This can also
    be serialized into save strings."""

    def __init__(self, scenes: list[TutorialScene]):

        self.scenes = scenes

    def __iter__(self):
        return iter(self.scenes)

    @classmethod
    def from_save_str(cls, save_str: str, /) -> Self:

        data = decompress(
            base64.a85decode(save_str.encode("utf-8")))
        return cls(pickle.loads(data))

    def as_save_str(self):

        encoded = compress(pickle.dumps(
            self.scenes
        ))

        save_str = base64.a85encode(encoded, wrapcol=0)
        return save_str.decode("utf-8")

# --- Animation Players ---

class Cutscene:

    """A class that plays a CutsceneData object."""

    START_PAUSE = 2.0
    END_PAUSE = 2.0

    def __init__(self, data: CutsceneData,
                 icon: str=None, username: str=None
                 ) -> None:

        """Takes in a CutsceneData object. Optionally,
        it takes in an icon and a username. If these
        are specified, they will be subbed into the
        map and dialogue respectively.
        """

        self.data = data
        self.icon = icon
        self.username = username

    def display_func(self, display: GameMap) -> GameMap:

        """Modifies the display by substituting the icon."""

        d = display.copy()

        if self.icon is not None:
            d.replace(Constants.NaC, self.icon)

        return d

    def text_func(self, text: str) -> str:

        """Modifies the dialogue by substituting the username."""

        if self.username is not None:
            return fill(text.replace("`", self.username), width=Constants.X_LEN)
        else:
            return text

    def run_dialogue(self, dialogue: Dialogue, *, speed: float=DEFAULT_SPEED):

        """Run the dialogue; display each line for its corresponding duration,
        one after the other.

        Optional arguments:
        - speed: an option to speed up the dialogue."""

        for line in dialogue:

            stdout.write(self.text_func(line.text) + "\n")
            sleep(line.duration / speed)

    def run_scene(self, scene: Scene, *, speed: float=DEFAULT_SPEED) -> None:

        """Runs a scene, first by printing the display, then by
        running the pause, and then playing the dialogue."""

        clear()
        stdout.write(str(self.display_func(scene.display)))

        if scene.pause is not None:
            sleep(scene.pause / speed)
        if scene.dialogue is not None:
            self.run_dialogue(scene.dialogue, speed=speed)

    def run(self, *,
            speed: float=DEFAULT_SPEED,
            allow_skip: bool=False
            ) -> None:

        """Runs a cutscene. There are two optional arguments:
        - speed: optionally speeds up the cutscene
        - allow_skip: asks users to skip in the beginning (default False)"""

        clear()

        if allow_skip:

            skip = IOUtils.get_validation("Skip cutscene? [y/n] ")

            if skip == IOUtils.Response.YES:
                return

        sleep(Cutscene.START_PAUSE) # Cinematic pause

        for scene in self.data:

            self.run_scene(scene, speed=speed)

        sleep(Cutscene.END_PAUSE)

class Tutorial:

    def __init__(self, tutorial_data: TutorialData, icon: str | None=None):

        self.data = tutorial_data
        self.icon = icon

    def run_scene(self, scene: TutorialScene):

        """Runs a tutorial by printing each slide with a delay,
        substituting an icon into each frame."""

        for _ in range(scene.repeat):

            for i, slide in enumerate(scene.slides):

                k = 1.3 if (i == 0 or i == len(scene) - 1) else 1.0

                clear()

                if self.icon is None:

                    stdout.write(str(slide))
                else:
                    stdout.write(str(slide.replaced(Constants.NaC, self.icon)))

                sleep(scene.speed * k)

    def run(self):

        for scene in self.data:

            while True:

                clear()

                if self.icon is None:
                    stdout.write(str(scene.thumbnail))
                else:
                    stdout.write(str(scene.thumbnail.replaced(Constants.NaC, self.icon)))

                if scene:
                    s = \
                        "Press: [p] to play animation, [Enter] for next slide, [x] to exit.\n"
                else:
                    s = \
                        "Animation not available. [Enter] for next slide, [x] to exit.\n"

                stdout.write(s)

                s = IOUtils.input("-> ", sanitize=True)

                match s:
                    case "p" if scene:
                        self.run_scene(scene)
                    case "":
                        break
                    case "x":
                        return

INTRO_DATA, ENDING_DATA = (
    CutsceneData.from_save_str(INTRO_STR),
    CutsceneData.from_save_str(ENDING_STR)
)

PLATFORMER_TUTORIAL = TutorialData.from_save_str(PLATFORMER_STR)
EDITOR_TUTORIAL = TutorialData.from_save_str(EDITOR_STR)
