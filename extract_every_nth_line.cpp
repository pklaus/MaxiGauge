#include <iostream>
#include <stdio.h>
#include <fstream>
#include <string>

#include <stdio.h>
#include <stdlib.h>

using namespace std;

int main( int argc, char* argv[] )
{
    ifstream input_file( argv[1] );
    int every_other = atoi(argv[2]);
    string line_of_file;

    if( ! input_file ) return 2;

    // We always want the first 2 lines:
    for (int i = 0; i <= 1; i++) {
        if( ! input_file ) return 3;
        getline( input_file, line_of_file );
        cout << line_of_file << endl;
    }

    if( ! input_file ) return 4;

    int lines_read = 0;
    while( !input_file.eof() ) {
        getline( input_file, line_of_file );
        if( input_file ) {
            ++lines_read;
            if( lines_read % every_other == 0 )
                //cout << "Read the line: " << line_of_file << endl;
                cout << line_of_file << endl;
        }
        else break;
    }
}
