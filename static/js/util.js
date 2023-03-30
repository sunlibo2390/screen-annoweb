function applyAjax(url, form, success, error) {
    let request = new XMLHttpRequest()
    request.open("POST", url)
    request.send(form)

    request.addEventListener("readystatechange", (xhr, e) => {
        if (request.readyState === 4) {
            if (request.status === 200) {
                if (success !== undefined) success(JSON.parse(request.responseText))
            } else if (error !== undefined) error(xhr, e)
        }
    })
}

class TaskHistory {
    constructor(task, template) {
        this.history = [task]
        this.template = template
        this.pivot = 0
    }

    current() { return this.history[this.pivot] }
    canUndo() { return this.pivot > 0 }
    canRedo() { return this.pivot < this.history.length - 1 }
    undo() { this.pivot = Math.max(this.pivot - 1, 0) }
    redo() { this.pivot = Math.min(this.pivot + 1, this.history.length - 1) }
    reset() { this.update(this.template) }
    np() { this.modifyRoleset(-3) }
    lv() { this.modifyRoleset(-4) }

    displayCurrent(tagMap) {
        let current = this.current()
        return [current[0], displayTags(current[1], tagMap)]
    }

    modifyRoleset(roleset) {
        this.update([roleset, roleset < 0 && roleset != -2 ? this.template[1] : this.current()[1]])
    }

    modifyTag(tagId, tagName, selection) {
        let current = this.current()
        this.update([current[0], annotate(current[1], tagId, tagName, selection)])
    }

    modifyAllTag(tag) {
        let current = this.current()
        this.update([current[0], tag])
    }

    update(task) {
        let current = this.current()
        let modified = task[0] !== current[0]
        for (let i = 0; i < task[1].length && !modified; i++) modified |= task[1][i] !== current[1][i]

        if (modified) {
            this.history = this.history.slice(0, this.pivot + 1)
            this.history.push(task)
            ++this.pivot
        }
    }
}

function displayTags(tags, tagMap) {
    let current = 0
    let result = []

    tags.forEach(tag => {
        if (tag === -1) result.push("")
        else {
            let newTag = tag >> 2
            let text = tagMap.get((newTag >> 2) & 31)

            if (newTag & 2) text = `R-${text}`
            if (newTag & 1) text = `C-${text}`

            let tagIndex = newTag >> 7
            if (tagIndex > 0) text = `${text} (${tagIndex})`
            result.push(`${text}-${('00' + current).slice(-2)}`)
        }

        current += tag !== -1 && (tag & 2)
    })

    return result
}

function extractTag(tag) { return tag.substring(0, tag.length - 3) }

function getSpannedTags(tags) {
    let current = tags[0]
    let span = 0
    let result = []

    tags.forEach(tag => {
        if (current === tag) ++span
        else {
            result.push([extractTag(current), span])
            span = 1
        }

        current = tag
    })

    result.push([extractTag(current), span])
    return result
}

function annotate(tags, tagId, tagName, selection) {
    if (selection.length === 0)
        return

    selection.sort((a, b) => a - b)
    let deletedArgs = new Set()
    let newTags = [...tags]

    selection.forEach(pos => {
        if (newTags[pos] >= 0) {
            let target = newTags[pos] >> 3
            deletedArgs.add(target)
            if (!(target & 1)) deletedArgs.add(target | 1)
        }
    })

    for (let i = 0; i < newTags.length; i++) {
        if (newTags[i] >= 0) {
            let current = newTags[i] >> 3
            if (deletedArgs.has(current)) newTags[i] = -1
        }
    }

    deletedArgs.forEach(arg => newTags = rearrangeTags(newTags, (arg >> 1) & 31))

    if (tagId !== -1) {
        let spans = new Map()
        let arg = tagId << 1

        for (let i = 0; i < newTags.length; i++) {
            let current = newTags[i]
            if (current === -1)
                continue

            let realTag = current >> 2
            let isContinue = realTag & 1
            realTag >>= 1

            if (((realTag >> 1) & 31) !== tagId)
                continue

            if (current & 1) {
                let span = [i, (current & 2) ? i + 1 : -1]
                if (isContinue) spans.get(realTag).push(span)
                else spans.set(realTag, span)
            } else if (current & 2) {
                let tagSpan = spans.get(realTag)
                let currentSpan = tagSpan[tagSpan.length - 1]
                tagSpan[tagSpan.length - 1] = [currentSpan[0], i + 1]
            }
        }

        if (tagName === "ARG-UNDEF" || tagName.slice(0, 4) === "ARGM") {
            let tagIndex = 0
            while (spans.has(tagIndex << 6 | arg)) ++tagIndex
            arg |= tagIndex << 6
        } else if (tagName !== "REL") arg |= spans.has(arg)

        if (spans.has(arg)) {
            for (let i = 0; i < newTags.length; i++) {
                if (newTags[i] >> 3 === arg) newTags[i] = -1
            }
        }

        arg <<= 3
        let stack = [selection[0]]

        for (let i = 1; i < selection.length; i++) {
            if (selection[i] != selection[i - 1] + 1) stack.push(selection[i - 1] + 1, selection[i])
        }

        stack.push(selection[selection.length - 1] + 1)

        for (let i = 0; i < stack.length; i += 2) {
            let start = stack[i], end = stack[i + 1]
            for (let j = start; j < end; j++) newTags[j] = arg
            newTags[start] |= 1
            newTags[end - 1] |= 2
            arg |= 4
        }

        newTags = rearrangeTags(newTags, tagId)
    }

    return newTags
}

function rearrangeTags(tags, protoArg) {
    let allArgs = new Set()
    let newTags = [...tags]

    tags.forEach(tag => {
        let arg = tag >> 2
        if (arg & 3)
            return
        arg >>= 2

        if ((arg & 31) === protoArg && !allArgs.has(arg)) {
            let newIndex = allArgs.size
            allArgs.add(arg)

            for (let i = 0; i < newTags.length; i++) {
                if ((tags[i] >> 4) === arg) newTags[i] = (newIndex << 9) | (tags[i] & 511)
            }
        }
    })

    return newTags
}
