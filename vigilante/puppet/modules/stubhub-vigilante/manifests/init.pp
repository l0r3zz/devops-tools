class stubhub-vigilante {
  File {
    owner => root,
    group => root,
    mode => 644,
  }
  
  
 file { '/usr/local/bin/phaktor.py':
    ensure => file,
    mode => 755,
    source => 'puppet:///modules/stubhub-vigilante/bin/phaktor.py',
  }
  
  file { '/usr/local/bin/phaktor':
    ensure => link,
    target => '/usr/local/bin/phaktor.py',
  }

  file { '/nas/reg/log/jiralab/vigilante/facts.ftr':
    ensure => file,
    source => 'puppet:///modules/stubhub-vigilante/etc/facts.ftr',
  }

  file { '/nas/reg/log/jiralab/vigilante/auditor':
    ensure => directory,
  }
 
 # NOTE: $phaktordepth needs to be set to the number of audits to keep 
  cron { "phaktor":
	user  => root,
	minute => fqdn_rand(60),
	hour => [0, 6, 12, 18 ]
    command => "phaktor -c /nas/reg/log/jiralab/vigilante/facts.ftr -r /nas/reg/log/jiralab/vigilante/auditor -d $phaktordepth",  
    require => File[ '/nas/reg/log/jiralab/vigilante/facts.ftr'],

  }

}
include stubhub-vigilante