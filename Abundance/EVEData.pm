#!/usr/bin/perl -w


use strict;

package Abundance::EVEData;

use base 'Exporter';
our @EXPORT_OK = qw ( );





our %resources = ( 
     'Barren' => { res_map =>  [ 'Aqueous Liquids', 'Base Metals', 'Carbon Compounds', 'Micro Organisms', 'Noble Metals' ],
                 typeid => 2016 },
    'Gas' =>  { res_map => [ 'Aqueous Liquids', 'Base Metals', 'Ionic Solutions', 'Noble Gas', 'Reactive Gas' ],
		typeid => 13 },
    'Ice' => { res_map => [ 'Aqueous Liquids', 'Heavy Metals', 'Micro Organisms', 'Noble Gas', 'Planktic Colonies' ] ,
	       typeid => 12 },
    'Lava' => { res_map => [ 'Base Metals', 'Felsic Magma', 'Heavy Metals',  'Non-CS Crystals', 'Suspended Plasma' ] ,
	       typeid => 2015 },
    'Oceanic' => { res_map => [ 'Aqueous Liquids', 'Carbon Compounds', 'Complex Organisms', 'Micro Organisms', 'Planktic Colonies' ] ,
	       typeid => 2014 },
    'Plasma' => { res_map => [ 'Base Metals', 'Heavy Metals', 'Noble Metals', 'Non-CS Crystals', 'Suspended Plasma' ],
	       typeid => 2063 },
    'Storm' => { res_map => [ 'Aqueous Liquids', 'Base Metals', 'Ionic Solutions',  'Noble Gas', 'Suspended Plasma' ],
	       typeid => 2017 },
    'Temperate' => { res_map => [ 'Aqueous Liquids', 'Autotrophs', 'Carbon Compounds', 'Complex Organisms', 'Micro Organisms' ],
	       typeid => 11 },
    'Shattered' => { res_map => [ 'R1', 'R2', 'R3', 'R4', 'R5' ] ,
	       typeid => 30889 },
    'Unknown' => { res_map => [ 'Resource 1', 'Resource 2', 'Resource 3', 'Resource 4', 'Resource 5' ], typeid => 999999 }
		    
    );

our %planet_types;

BEGIN {
    foreach my $name ( keys %resources ) {
	my $typeid = $resources{$name}->{typeid};
	$planet_types {$typeid} = $name;
    }
}

1;
