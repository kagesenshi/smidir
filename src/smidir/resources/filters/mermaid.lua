local system = require 'pandoc.system'

-- Helper to check if file exists
local function file_exists(name)
   local f = io.open(name, "r")
   if f ~= nil then io.close(f) return true else return false end
end

-- Create a hash of the content to use as filename
local function get_hash(content)
  return pandoc.sha1(content)
end

-- Generate a unique temporary directory for images
-- os.tmpname() returns a path to a file, so we remove it and create a directory
local img_dir = os.tmpname()
os.execute('rm -f ' .. img_dir .. ' && mkdir -p ' .. img_dir)

function CodeBlock(block)
  if block.classes:includes('mermaid') then
    local content = block.text
    local hash = get_hash(content)
    local filename = img_dir .. '/' .. hash .. '.svg'
    
    -- Check if file already exists
    if not file_exists(filename) then
      local width = block.attributes['width'] or '800'
      
      -- We'll use a temporary file for the mermaid code
      local mmd_file = os.tmpname()
      local f = io.open(mmd_file, 'w')
      f:write(content)
      f:close()
      
      -- Use a temporary file for the intermediate PDF
      -- Note: os.tmpname() might not have .pdf extension, so we append it
      local pdf_file = os.tmpname() .. '.pdf'
      
      -- Step 1: Generate PDF using mmdc
      -- The command specified by user: npx -p @mermaid-js/mermaid-cli mmdc
      local mmdc_cmd = string.format('npx -p @mermaid-js/mermaid-cli mmdc -i %s -o %s -w %s --pdfFit', mmd_file, pdf_file, width)
      
      print('Generating mermaid PDF: ' .. pdf_file .. ' (width: ' .. width .. ')')
      local mmdc_success = os.execute(mmdc_cmd)
      
      if mmdc_success then
        -- Step 2: Convert PDF to SVG for better compatibility
        local pdf2svg_cmd = string.format('pdf2svg %s %s', pdf_file, filename)
        
        print('Converting PDF to SVG: ' .. filename)
        local pdf2svg_success = os.execute(pdf2svg_cmd)
        
        -- Cleanup temporary files
        os.remove(mmd_file)
        os.remove(pdf_file)
        
        if not pdf2svg_success then
          io.stderr:write("Error: Failed to execute pdf2svg for " .. filename .. "\n")
          return block -- Fallback to code block on error
        end
      else
        -- Cleanup temporary file
        os.remove(mmd_file)
        -- Termporary PDF might not have been created if mmdc failed
        os.remove(pdf_file)
        
        io.stderr:write("Error: Failed to execute mmdc for " .. filename .. "\n")
        return block -- Fallback to code block on error
      end
    end
    
    -- Return an image para
    return pandoc.Para({
      pandoc.Image({pandoc.Str(content)}, filename, "")
    })
  end
end
