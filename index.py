#!/usr/bin/python3
import re
import nltk
import sys
import getopt
import os
import pickle
import shutil

ps = nltk.stem.PorterStemmer()


def usage():
    print(
        "usage: "
        + sys.argv[0]
        + " -i directory-of-documents -d dictionary-file -p postings-file"
    )


# Resets the disk folder
def reset_disk():
    dir_name = os.path.join(os.path.dirname(__file__), "disk")
    if os.path.exists(dir_name):
        shutil.rmtree(dir_name)
    os.mkdir(dir_name)


def write_term_postings_dict_to_disk(term_postings_dict, block_num):
    # Get disk directory to write to
    dir_name = os.path.join(os.path.dirname(__file__), "disk")

    # Write full block from main memory to disk
    file_name = os.path.join(dir_name, "block_{}".format(block_num))
    with open(file_name, "wb") as outfile:  # Serialize block's dictionary to disk
        # Sort the postings lists according to the term lexicographically, and the postings list in numerical ascending order
        for term in sorted(term_postings_dict.keys()):
            postings_list = sorted(term_postings_dict[term])
            term_postings = [term, postings_list]
            pickle.dump(
                term_postings, outfile
            )  # Store each <term, postings list> to the disk block
        outfile.close()


def build_index(in_dir, out_dict, out_postings):
    """
    build index from documents stored in the input directory,
    then output the dictionary file and postings file
    """
    print("indexing...\n")
    # This is an empty method
    # Pls implement your code in below

    # Define constants (in bytes)
    BLOCK_SIZE = 5000000  # Size of a block (main memory)
    CHUNK_SIZE = 500000  # Size of a chunk that we load from each block to merge

    # Reset disk
    reset_disk()

    # Define variables
    term_postings_dict = (
        {}
    )  # The current dictionary <term, [posting_list]> for each of the blocks
    block_num = (
        1  # Block number to write out intermediate blocks to disk (block file name)
    )
    size_used = 0

    # Read in documents to index
    docIDs = os.listdir(in_dir)  # Read in paths of all documents in the in_dir

    # Subset of paths for testing purposes
    docIDs = docIDs[:2500]

    # Process every document and create a dictionary of posting lists
    for docID in docIDs:
        f = open(os.path.join(in_dir, docID), "r")  # Open the document file
        text = f.read()  # Read the document in fulltext
        text = text.lower()  # Convert text to lower case
        sentences = nltk.sent_tokenize(text)  # Tokenize by sentence

        for sentence in sentences:
            words = nltk.word_tokenize(sentence)  # Tokenize by word
            words_stemmed = [ps.stem(w) for w in words]  # Stem every word

            for word in words_stemmed:
                # Before we add anything to the dictionary, we need to check that it will not exceed main memory
                # CASE 1: Check if word doesn't exist in dictionary
                if word not in term_postings_dict:
                    word_posting_size = sys.getsizeof(word) + sys.getsizeof(docID)

                    # Check that if we add this new term in, we won't exceed the block's memory size
                    # If exceed, we need to write block to disk (temporary postings file) and clear the memory
                    if word_posting_size + size_used > BLOCK_SIZE:
                        write_term_postings_dict_to_disk(
                            term_postings_dict, block_num
                        )  # Write block's dictionary to disk
                        block_num += (
                            1  # Increase block number that we have stored in disk
                        )
                        size_used = 0  # Reset size used in main memory
                        term_postings_dict.clear()  # Clear the in memory dictionary for the next block

                    # Add new term into block's dictionary
                    term_postings_dict[word] = [docID]
                    size_used += word_posting_size  # Increase size used in main memory

                # CASE 2: If word is inside dictionary
                else:
                    # If docID is not inside the postings list, need to check if we have memory to add to postings list
                    # If docID is already inside the postings list for this term, don't need to do anything
                    if docID not in term_postings_dict[word]:
                        # If exceed, we need to write block to disk (temporary postings file) and clear the memory
                        docID_size = sys.getsizeof(docID)

                        if docID_size + size_used > BLOCK_SIZE:
                            write_term_postings_dict_to_disk(
                                term_postings_dict, block_num
                            )  # Write block's dictionary to disk
                            block_num += (
                                1  # Increase block number that we have stored in disk
                            )
                            size_used = 0  # Reset size used in main memory
                            term_postings_dict.clear()  # Clear the in memory dictionary for the next block

                            # We need to add the the term to the cleared dictionary
                            term_postings_dict[word] = [docID]
                            size_used += (
                                sys.getsizeof(word) + docID_size
                            )  # Increase size of main memory used
                        else:
                            # The dictionary is still in main memory and we can just append the new docID to the postings list
                            term_postings_dict[word].append(docID)
                            size_used += docID_size  # Increase size of main memory used

        # Close the file
        f.close()

    # Write out the last block in main memory to the disk
    write_term_postings_dict_to_disk(
        term_postings_dict, block_num
    )  # Write block's dictionary to disk
    block_num += 1  # Increase block number that we have stored in disk
    size_used = 0  # Reset size used in main memory
    term_postings_dict.clear()  # Clear the in memory dictionary for the next block

    # Now we need to load each block chunk by chunk and do a single pass merge

    # if word not in dictionary:  # new word/term, add to dictionary
    #     dictionary[word] = {
    #         "docFreq": 1,
    #         "termID": termID,
    #         "postingListPointer": termID,
    #     }  # postingListPointer same as termID for now
    #     postingLists.append([docID])
    #     termID += 1
    # else:  # word is in dictionary
    #     if (
    #         docID
    #         not in postingLists[dictionary[word]["postingListPointer"]]
    #     ):  # check if docID already in the corresponding postingList
    #         postingLists[dictionary[word]["postingListPointer"]].append(
    #             docID
    #         )  # append docID to end of corresponding postingList if not exists
    #         dictionary[word]["docFreq"] += 1


# Main

input_directory = output_file_dictionary = output_file_postings = None

try:
    opts, args = getopt.getopt(sys.argv[1:], "i:d:p:")
except getopt.GetoptError:
    usage()
    sys.exit(2)

for o, a in opts:
    if o == "-i":  # input directory
        input_directory = a
    elif o == "-d":  # dictionary file
        output_file_dictionary = a
    elif o == "-p":  # postings file
        output_file_postings = a
    else:
        assert False, "unhandled option"

if (
    input_directory == None
    or output_file_postings == None
    or output_file_dictionary == None
):
    usage()
    sys.exit(2)

build_index(input_directory, output_file_dictionary, output_file_postings)
