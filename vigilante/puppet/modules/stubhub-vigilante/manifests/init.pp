class stubhub-vigilante {
  File {
    owner => root,
    group => root,
    mode => 644,
  }
  
 # schedule { 'audit' :
 #    period => daily,
 #   range => "$startwindow - $endwindow",
 # }
  
 file { '/usr/local/bin/phaktor.py':
    ensure => file,
    mode => 755,
    source => 'puppet:///modules/stubhub-vigilante/files/phaktor.py',
  }
  
  file { '/usr/local/bin/phaktor':
    ensure => link,
    target => '/usr/local/bin/phaktor.py',
    # needed? require => File['/usr/local/bin/phaktor.py'],
  }

  file { '/nas/reg/log/jiralab/vigilante/facts.ftr':
    ensure => file,
    source => 'puppet:///modules/stubhub-vigilante/files/facts.ftr',
  }

  file { '/nas/reg/log/jiralab/vigilante/auditor':
    ensure => directory,
  }
  
  exec { "phaktor":
    #schedule => 'audit',
    command => "phaktor -c /nas/reg/log/jiralab/vigilante/facts.ftr -r /nas/reg/log/jiralab/vigilante/auditor ",
    path    => "/usr/local/bin:/nas/reg/bin/jiralab/:/bin/:/usr/bin/",
    logoutput => true,
    # needed? require => File['/nas/reg/log/jiralab/vigilante/auditor'],
    require => File[ '/nas/reg/log/jiralab/vigilante/facts.ftr'],

  }

}
include stubhub-vigilante