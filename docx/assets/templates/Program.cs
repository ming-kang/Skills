// Program.cs - Minimal local-first document template.
// Replace this file with your actual document generator logic.

using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;

string defaultOutput = Path.Combine(Environment.CurrentDirectory, "output.docx");
string output = Path.GetFullPath(args.Length > 0 ? args[0] : defaultOutput);
string? outputDir = Path.GetDirectoryName(output);

if (!string.IsNullOrEmpty(outputDir))
{
    Directory.CreateDirectory(outputDir);
}

using (var doc = WordprocessingDocument.Create(output, DocumentFormat.OpenXml.WordprocessingDocumentType.Document))
{
    var mainPart = doc.AddMainDocumentPart();
    mainPart.Document = new Document(
        new Body(
            new Paragraph(
                new Run(
                    new Text("KimiDocx local template generated this placeholder document.")
                )
            ),
            new Paragraph(
                new Run(
                    new Text("Edit .docx/Program.cs to replace this content with your real document logic.")
                )
            )
        )
    );
    mainPart.Document.Save();
}

Console.WriteLine($"Generated: {output}");
