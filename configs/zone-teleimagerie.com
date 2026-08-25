$TTL 3600
@	IN SOA dns14.ovh.net. tech.ovh.net. (2085951314 86400 3600 3600000 60)
        IN NS     dns14.ovh.net.
        IN NS     ns14.ovh.net.
        IN MX     5 mx2.mail.ovh.net.
        IN MX     1 mx1.mail.ovh.net.
        IN MX     100 mx3.mail.ovh.net.
        IN A     213.186.33.5
        IN TXT     "v=spf1 include:mx.ovh.com -all"
        IN TXT     "1|www.teleimagerie.com"
ftp        IN CNAME     teleimagerie.com.
www        IN A     213.186.33.5
www        IN TXT     "3|welcome"
