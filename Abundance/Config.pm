#!/usr/bin/perl -w


use strict;

package Abundance::Config;

use base 'Exporter';
our @EXPORT_OK = qw ( debug_level );

our $debug_level = 5;

sub debug_level {
    return $debug_level;
}


#  Database
our $dsn = "DBI:mysql:database=db_euni;host=mysql.isp.net";
our $dbuser = "eveuser";
our $dbpass = "password";

our $imagedir = "resourceblock";

our $write_orig = 1;

our $have_display = 1;
1;
