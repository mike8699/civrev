// dump_xex_image — link against XenonUtils, load a XEX, write the
// decompressed/decrypted image to stdout (or a file).
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <vector>
#include <fstream>
#include "image.h"
#include "xex.h"

int main(int argc, char** argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: dump_xex_image <input.xex> <output.bin>\n");
        return 2;
    }
    std::ifstream f(argv[1], std::ios::binary | std::ios::ate);
    if (!f) { fprintf(stderr, "open failed\n"); return 1; }
    size_t sz = f.tellg();
    f.seekg(0);
    std::vector<uint8_t> buf(sz);
    f.read((char*)buf.data(), sz);
    Image image = Xex2LoadImage(buf.data(), buf.size());
    if (!image.data) {
        fprintf(stderr, "Xex2LoadImage failed\n");
        return 1;
    }
    std::ofstream out(argv[2], std::ios::binary);
    out.write((const char*)image.data.get(), image.size);
    fprintf(stderr, "wrote %zu bytes, base=%zx\n", (size_t)image.size, (size_t)image.base);
    return 0;
}
