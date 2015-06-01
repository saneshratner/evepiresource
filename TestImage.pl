#!/usr/bin/perl -w


use Abundance::Image qw (extract_image extract_image_file);


my $filename = shift @ARGV;

if  (!  defined $filename ) {
    $filename = "resourceblock/2015_05_04_08_15_09.png";
}


open (INFILE, "<$filename") or die "Unable to open file ($filename): $!\n";

($success, $resblockfile, $resource_valuesref) = extract_image_file (*INFILE, "ASystem", "5");

@resource_values = @{$resource_valuesref};

printf ("Success = %d, BlockFile = %s, values = (%s)\n", 
	$success, $resblockfile, join (", ", @resource_values));
	
